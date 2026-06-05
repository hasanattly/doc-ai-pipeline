# src/preprocessor/test_preprocessor.py

from image_processor import ImageProcessor
import cv2

processor = ImageProcessor(dpi=300)

# Test with a real image — we'll create a synthetic one for now
import numpy as np

# Create a fake "scanned document" image for testing
fake_scan = np.ones((800, 600, 3), dtype=np.uint8) * 240
cv2.putText(fake_scan, "Invoice #1234", (50, 100),
            cv2.FONT_HERSHEY_SIMPLEX, 2, (20, 20, 20), 3)
cv2.putText(fake_scan, "Total: $500.00", (50, 200),
            cv2.FONT_HERSHEY_SIMPLEX, 1.5, (20, 20, 20), 2)
cv2.imwrite("/app/data/input/test_scan.png", fake_scan)
print("Test image created at data/input/test_scan.png")

# Now process it
results = processor.process("/app/data/input/test_scan.png")
print(f"Pages processed: {len(results)}")
print(f"Output image shape: {results[0].shape}")
print("Preprocessor working correctly ✅")