# src/ocr/ocr_engine.py

import easyocr
import numpy as np
from pathlib import Path
from dataclasses import dataclass, field
from loguru import logger


# ──────────────────────────────────────────────
# DATA STRUCTURES
# ──────────────────────────────────────────────

@dataclass
class OCRBlock:
    """
    Represents a single detected text block from OCR.
    Captures everything — not just the text, but WHERE it is
    and HOW confident the model is. This is what separates
    a production pipeline from a basic script.
    """
    page_number: int          # Which page this came from
    text: str                 # The extracted text
    confidence: float         # Model confidence (0.0 → 1.0)
    bounding_box: list        # [[x1,y1],[x2,y2],[x3,y3],[x4,y4]]
    x_min: int = 0            # Leftmost pixel coordinate
    y_min: int = 0            # Topmost pixel coordinate
    x_max: int = 0            # Rightmost pixel coordinate
    y_max: int = 0            # Bottommost pixel coordinate


@dataclass
class PageResult:
    """
    Represents the full OCR result for one page.
    Contains all blocks found on that page plus metadata.
    """
    page_number: int
    blocks: list[OCRBlock] = field(default_factory=list)
    raw_text: str = ""        # All text joined as a single string
    total_blocks: int = 0
    avg_confidence: float = 0.0


@dataclass
class DocumentResult:
    """
    Top-level result for an entire document (all pages).
    This is what gets passed to the parser in Phase 4.
    """
    file_name: str
    total_pages: int
    pages: list[PageResult] = field(default_factory=list)
    full_text: str = ""       # Entire document text joined


# ──────────────────────────────────────────────
# OCR ENGINE
# ──────────────────────────────────────────────

class OCREngine:
    """
    Wraps EasyOCR with production-grade structure.
    Accepts preprocessed images from ImageProcessor.
    Returns a DocumentResult with full text, positions,
    and confidence scores for every detected block.
    """

    def __init__(self, languages: list[str] = ["en"], gpu: bool = False):
        """
        Args:
            languages: List of language codes EasyOCR should detect.
                      e.g. ["en"], ["en", "fr"], ["en", "hi"]
            gpu: Set True if CUDA GPU is available for faster inference.
                 We default to False for CPU-safe Docker environments.
        """
        logger.info(f"Initializing EasyOCR | languages={languages} | gpu={gpu}")
        # EasyOCR downloads model weights on first run (~100MB)
        # Subsequent runs use the cached model — much faster
        self.reader = easyocr.Reader(languages, gpu=gpu)
        logger.success("EasyOCR engine ready")

    # ──────────────────────────────────────────────
    # PUBLIC ENTRY POINT
    # ──────────────────────────────────────────────

    def extract(
        self,
        images: list[np.ndarray],
        file_name: str = "document"
    ) -> DocumentResult:
        """
        Main method. Accepts preprocessed images from ImageProcessor.
        Returns a fully structured DocumentResult.

        Args:
            images: List of preprocessed numpy arrays (one per page)
            file_name: Original filename for metadata tracking

        Returns:
            DocumentResult containing all pages, blocks, and text
        """
        logger.info(f"Starting OCR on '{file_name}' — {len(images)} page(s)")

        document = DocumentResult(
            file_name=file_name,
            total_pages=len(images)
        )

        all_text = []

        for i, img in enumerate(images):
            page_num = i + 1
            logger.info(f"Running OCR on page {page_num}/{len(images)}")

            page_result = self._process_page(img, page_num)
            document.pages.append(page_result)
            all_text.append(page_result.raw_text)

            logger.info(
                f"Page {page_num} done — "
                f"{page_result.total_blocks} blocks | "
                f"avg confidence: {page_result.avg_confidence:.2f}"
            )

        document.full_text = "\n\n--- PAGE BREAK ---\n\n".join(all_text)
        logger.success(f"OCR complete — {len(document.pages)} page(s) extracted")

        return document

    # ──────────────────────────────────────────────
    # PAGE PROCESSING
    # ──────────────────────────────────────────────

    def _process_page(
        self,
        img: np.ndarray,
        page_number: int
    ) -> PageResult:
        """
        Runs EasyOCR on a single page image.
        Parses raw EasyOCR output into clean OCRBlock objects.
        """
        # EasyOCR returns: list of [bounding_box, text, confidence]
        raw_results = self.reader.readtext(img)

        page = PageResult(page_number=page_number)
        confidences = []

        for detection in raw_results:
            bounding_box, text, confidence = detection

            # Skip very low confidence detections (likely noise)
            if confidence < 0.1:
                logger.debug(f"Skipping low confidence block: '{text}' ({confidence:.2f})")
                continue

            # Extract flat coordinates from bounding box
            x_coords = [point[0] for point in bounding_box]
            y_coords = [point[1] for point in bounding_box]

            block = OCRBlock(
                page_number=page_number,
                text=text.strip(),
                confidence=round(confidence, 4),
                bounding_box=bounding_box,
                x_min=int(min(x_coords)),
                y_min=int(min(y_coords)),
                x_max=int(max(x_coords)),
                y_max=int(max(y_coords))
            )

            page.blocks.append(block)
            confidences.append(confidence)

        # ── Assemble raw text preserving line structure ──
        # Group blocks into lines by Y-coordinate proximity
        # Blocks within 15px vertically are considered the same line
        sorted_blocks = sorted(page.blocks, key=lambda b: (b.y_min, b.x_min))

        lines = []
        current_line_blocks = []
        current_y = None

        for block in sorted_blocks:
            if current_y is None:
                current_y = block.y_min
                current_line_blocks.append(block)
            elif abs(block.y_min - current_y) <= 15:
                # Same line — append to current group
                current_line_blocks.append(block)
            else:
                # New line detected — save current and start fresh
                line_text = " ".join(b.text for b in
                            sorted(current_line_blocks, key=lambda b: b.x_min))
                lines.append(line_text)
                current_line_blocks = [block]
                current_y = block.y_min

        # Don't forget the last line
        if current_line_blocks:
            line_text = " ".join(b.text for b in
                        sorted(current_line_blocks, key=lambda b: b.x_min))
            lines.append(line_text)

        page.raw_text = "\n".join(lines)
        page.total_blocks = len(page.blocks)
        page.avg_confidence = round(
            sum(confidences) / len(confidences), 4
        ) if confidences else 0.0

        return page