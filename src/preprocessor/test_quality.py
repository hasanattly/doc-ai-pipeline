# src/preprocessor/test_quality.py
import sys
import numpy as np
sys.path.append("/app/src")
from preprocessor.image_processor import ImageProcessor
from PIL import Image

processor = ImageProcessor()
img = np.array(Image.open("/app/data/input/test_invoice.png").convert("L"))
score = processor._assess_quality(img)
std_dev = np.std(img)

print(f"Quality score: {score}")
print(f"Std dev: {std_dev:.2f}")
print(f"Will use: {'minimal' if score >= 0.7 else 'full'} preprocessing")