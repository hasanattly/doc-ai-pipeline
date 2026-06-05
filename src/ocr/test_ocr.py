# src/ocr/test_ocr.py

import sys
sys.path.append("/app/src")

from preprocessor.image_processor import ImageProcessor
from ocr.ocr_engine import OCREngine
import numpy as np
import cv2

# ── Step 1: Create a test image with real text ──
fake_doc = np.ones((800, 600, 3), dtype=np.uint8) * 255
texts = [
    ("INVOICE", (50, 80), 2.0),
    ("Invoice #: INV-2024-001", (50, 180), 0.9),
    ("Date: 12/01/2024", (50, 260), 0.9),
    ("Item: Python Consulting", (50, 340), 0.9),
    ("Amount: $1,500.00", (50, 420), 0.9),
    ("Total Due: $1,500.00", (50, 500), 1.0),
]
for text, pos, scale in texts:
    cv2.putText(fake_doc, text, pos,
                cv2.FONT_HERSHEY_SIMPLEX, scale, (0, 0, 0), 2)

cv2.imwrite("/app/data/input/test_invoice.png", fake_doc)
print("Test invoice image created ✅")

# ── Step 2: Preprocess ──
processor = ImageProcessor(dpi=300)
images = processor.process("/app/data/input/test_invoice.png")
print(f"Preprocessed pages: {len(images)}")

# ── Step 3: Run OCR ──
engine = OCREngine(languages=["en"], gpu=False)
result = engine.extract(images, file_name="test_invoice.png")

# ── Step 4: Print Results ──
print(f"\nDocument: {result.file_name}")
print(f"Total pages: {result.total_pages}")
print(f"\n--- Extracted Blocks ---")
for block in result.pages[0].blocks:
    print(f"  [{block.confidence:.2f}] '{block.text}' @ ({block.x_min},{block.y_min})")

print(f"\n--- Full Text ---")
print(result.full_text)
print(f"\nAvg Confidence: {result.pages[0].avg_confidence}")
print("\nOCR Engine working correctly ✅")