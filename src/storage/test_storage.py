# src/storage/test_storage.py
import sys
sys.path.append("/app/src")

from preprocessor.image_processor import ImageProcessor
from ocr.ocr_engine import OCREngine
from parser.document_parser import DocumentParser
from storage.storage_manager import StorageManager

# ── Run full pipeline ──
processor = ImageProcessor()
images    = processor.process("/app/data/input/test_invoice.png")

engine = OCREngine(languages=["en"], gpu=False)
result = engine.extract(images, file_name="test_invoice.png")

parser = DocumentParser()
parsed = parser.parse(result)

# ── Save to database ──
storage = StorageManager()
doc_id  = storage.save(parsed)

# ── Read back and verify ──
print("\n--- All Documents in DB ---")
for doc in storage.get_all_documents():
    print(f"  ID={doc['id']} | {doc['document_type']} | {doc['file_name']} | confidence={doc['confidence_score']}")

print("\n--- Full Document Detail ---")
detail = storage.get_document_by_id(doc_id)
print(f"  File        : {detail['file_name']}")
print(f"  Type        : {detail['document_type']}")
print(f"  Confidence  : {detail['confidence_score']}")
print(f"\n  Fields:")
for k, v in detail["fields"].items():
    print(f"    {k:20s} → {v}")
print(f"\n  Line Items:")
for item in detail["line_items"]:
    print(f"    {item['description']:40s} {item['amount']}")

print("\nStorage layer working correctly ✅")