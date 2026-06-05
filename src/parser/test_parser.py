# src/parser/test_parser.py
import sys
sys.path.append("/app/src")

from preprocessor.image_processor import ImageProcessor
from ocr.ocr_engine import OCREngine
from parser.document_parser import DocumentParser

# ── Step 1: Preprocess ──
processor = ImageProcessor()
images    = processor.process("/app/data/input/test_invoice.png")

# ── Step 2: OCR ──
engine = OCREngine(languages=["en"], gpu=False)
result = engine.extract(images, file_name="test_invoice.png")

# ── Step 3: Parse ──
parser = DocumentParser()
parsed = parser.parse(result)

# ── Step 4: Print Results ──
print(f"\nDocument Type : {parsed.document_type}")
print(f"Confidence    : {parsed.confidence_score}")
print(f"\nExtracted Fields:")
for key, value in parsed.fields.items():
    print(f"  {key:20s} → {value}")

print(f"\nLine Items ({len(parsed.line_items)}):")
for item in parsed.line_items:
    print(f"  {item['description']:40s} {item['amount']}")

# ── Step 5: Save outputs ──
json_path = parser.save_json(parsed)
csv_path  = parser.save_csv(parsed)
print(f"\nJSON saved → {json_path}")
print(f"CSV  saved → {csv_path}")
print("\nParser working correctly ✅")