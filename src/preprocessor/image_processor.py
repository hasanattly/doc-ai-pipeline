# src/preprocessor/image_processor.py

import fitz                  # PyMuPDF — PDF handling
import cv2                   # OpenCV — image processing
import numpy as np           # Numerical operations on image arrays
from pathlib import Path     # Clean file path handling
from loguru import logger    # Production-style logging


class ImageProcessor:
    """
    Handles all image preprocessing before OCR.
    Accepts either a PDF file or a raw image (JPG/PNG).
    Outputs a list of cleaned, OCR-ready numpy arrays.
    """

    SUPPORTED_IMAGE_FORMATS = {".jpg", ".jpeg", ".png", ".bmp", ".tiff"}

    def __init__(self, dpi: int = 300):
        """
        Args:
            dpi: Resolution for PDF to image conversion.
                 300 DPI is the gold standard for OCR accuracy.
        """
        self.dpi = dpi
        logger.info(f"ImageProcessor initialized with DPI={dpi}")

    # ──────────────────────────────────────────────
    # PUBLIC ENTRY POINT
    # ──────────────────────────────────────────────

    def process(self, file_path: str) -> list[np.ndarray]:
        """
        Main method. Accepts a PDF or image path.
        Returns a list of preprocessed images (one per page).

        Args:
            file_path: Path to the input PDF or image file.

        Returns:
            List of preprocessed numpy arrays ready for OCR.
        """
        path = Path(file_path)

        if not path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        if path.suffix.lower() == ".pdf":
            logger.info(f"Processing PDF: {path.name}")
            raw_images = self._pdf_to_images(path)
        elif path.suffix.lower() in self.SUPPORTED_IMAGE_FORMATS:
            logger.info(f"Processing Image: {path.name}")
            raw_images = self._load_image(path)
        else:
            raise ValueError(f"Unsupported file type: {path.suffix}")

        # Run each page/image through the preprocessing pipeline
        processed = []
        for i, img in enumerate(raw_images):
            logger.info(f"Preprocessing page {i + 1}/{len(raw_images)}")
            clean_img = self._preprocess(img)
            processed.append(clean_img)

        logger.success(f"Preprocessing complete — {len(processed)} page(s) ready")
        return processed

    # ──────────────────────────────────────────────
    # FILE LOADING
    # ──────────────────────────────────────────────

    def _pdf_to_images(self, path: Path) -> list[np.ndarray]:
        """
        Converts each page of a PDF into a numpy image array.
        Uses PyMuPDF (fitz) for fast, accurate rendering.
        """
        images = []
        pdf_document = fitz.open(str(path))

        for page_num in range(len(pdf_document)):
            page = pdf_document[page_num]

            # Matrix controls resolution — higher = better OCR accuracy
            zoom = self.dpi / 72  # 72 is PDF's default DPI
            matrix = fitz.Matrix(zoom, zoom)

            # Render page to a pixel map then convert to numpy array
            pixmap = page.get_pixmap(matrix=matrix)
            img_array = np.frombuffer(pixmap.samples, dtype=np.uint8)
            img_array = img_array.reshape(pixmap.height, pixmap.width, pixmap.n)

            # Convert RGBA → RGB if needed
            if pixmap.n == 4:
                img_array = cv2.cvtColor(img_array, cv2.COLOR_RGBA2RGB)

            images.append(img_array)
            logger.debug(f"Page {page_num + 1} rendered at {self.dpi} DPI")

        pdf_document.close()
        return images

    def _load_image(self, path: Path) -> list[np.ndarray]:
        """
        Loads a single image file into a numpy array.
        Returns a list for consistency with _pdf_to_images.
        """
        img = cv2.imread(str(path))
        if img is None:
            raise ValueError(f"OpenCV could not read image: {path}")
        # OpenCV loads as BGR → convert to RGB
        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        return [img]

    # ──────────────────────────────────────────────
    # PREPROCESSING PIPELINE
    # ──────────────────────────────────────────────

    def _preprocess(self, img: np.ndarray) -> np.ndarray:
        """
        Adaptive preprocessing pipeline.
        Applies heavy cleaning only when the image actually needs it.
        Clean digital images get minimal processing.
        Poor quality scans get the full pipeline.
        """
        img = self._to_grayscale(img)

        quality = self._assess_quality(img)
        logger.info(f"Image quality score: {quality:.2f}")

        if quality >= 0.5:
            # Clean image — minimal processing to avoid distortion
            logger.info("Clean image detected — applying minimal preprocessing")
            return img
        else:
            # Poor quality scan — apply full pipeline
            logger.info("Low quality scan detected — applying full preprocessing")
            img = self._denoise(img)
            img = self._threshold(img)
            img = self._deskew(img)
            return img

    def _assess_quality(self, img: np.ndarray) -> float:
        """
        Estimates image quality using contrast and sharpness.
        Returns a score between 0.0 (poor) and 1.0 (clean).
        High std deviation = good contrast = clean document.
        """
        std_dev = np.std(img)
        score = min(std_dev / 40.0, 1.0)
        return round(score, 4)

   
    # Normalize: a std_dev of ~40+ means clean document
    # (lowered from 80 to better match real document characteristics)
    
    def _to_grayscale(self, img: np.ndarray) -> np.ndarray:
        """Converts RGB image to grayscale for OCR processing."""
        if len(img.shape) == 3:
            return cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
        return img  # Already grayscale

    def _denoise(self, img: np.ndarray) -> np.ndarray:
        """
        Removes scanner noise and artifacts using Gaussian blur.
        Kernel size (5,5) is a safe default for document scans.
        """
        return cv2.GaussianBlur(img, (5, 5), 0)

    def _threshold(self, img: np.ndarray) -> np.ndarray:
        """
        Converts grayscale to pure black and white.
        Otsu's method automatically finds the optimal threshold value —
        no manual tuning needed, works across different scan qualities.
        """
        _, binary = cv2.threshold(
            img, 0, 255,
            cv2.THRESH_BINARY + cv2.THRESH_OTSU
        )
        return binary

    def _deskew(self, img: np.ndarray) -> np.ndarray:
        """
        Detects and corrects page tilt (common in scanned documents).
        Uses image moments to calculate the skew angle and rotates to fix it.
        Skips correction if tilt is under 0.5 degrees (negligible).
        """
        # Find coordinates of all non-zero (black text) pixels
        coords = np.column_stack(np.where(img < 128))

        if len(coords) < 100:
            logger.debug("Not enough content to deskew — skipping")
            return img

        # Calculate the minimum bounding rectangle around the text
        angle = cv2.minAreaRect(coords)[-1]

        # Normalize the angle to the range (-45, 45)
        if angle < -45:
            angle = -(90 + angle)
        else:
            angle = -angle

        if abs(angle) < 0.5:
            logger.debug(f"Skew angle {angle:.2f}° — no correction needed")
            return img

        logger.debug(f"Correcting skew angle: {angle:.2f}°")

        # Rotate image to correct the skew
        (h, w) = img.shape[:2]
        center = (w // 2, h // 2)
        rotation_matrix = cv2.getRotationMatrix2D(center, angle, 1.0)
        corrected = cv2.warpAffine(
            img, rotation_matrix, (w, h),
            flags=cv2.INTER_CUBIC,
            borderMode=cv2.BORDER_REPLICATE
        )
        return corrected