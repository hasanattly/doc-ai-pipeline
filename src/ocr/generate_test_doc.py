# src/ocr/generate_test_doc.py
from PIL import Image, ImageDraw, ImageFont
import os

# Create a clean white document
img = Image.new("RGB", (800, 1000), color=(255, 255, 255))
draw = ImageDraw.Draw(img)

# Use default Pillow font (clean and OCR-friendly)
lines = [
    (50, 60,  28, "INVOICE"),
    (50, 130, 20, "Invoice #: INV-2024-001"),
    (50, 180, 20, "Date: 12/01/2024"),
    (50, 230, 20, "Bill To: John Smith"),
    (50, 280, 20, "Address: 123 Main Street, NY"),
    (50, 360, 22, "ITEMS"),
    (50, 410, 18, "Python Consulting      10hrs    $150/hr"),
    (50, 460, 18, "Data Pipeline Setup     5hrs    $150/hr"),
    (50, 560, 22, "Subtotal:   $2,250.00"),
    (50, 610, 22, "Tax (10%):  $225.00"),
    (50, 660, 24, "TOTAL DUE:  $2,475.00"),
    (50, 780, 16, "Payment due within 30 days."),
    (50, 820, 16, "Bank: First National   Acc: 9876543210"),
]

for x, y, size, text in lines:
    font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", size) \
        if os.path.exists("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf") \
        else ImageFont.load_default()
    draw.text((x, y), text, fill=(0, 0, 0), font=font)

# Draw a separator line
draw.line([(50, 390), (750, 390)], fill=(0, 0, 0), width=2)
draw.line([(50, 540), (750, 540)], fill=(0, 0, 0), width=2)

img.save("/app/data/input/test_invoice.png")
print("Clean test invoice generated ✅")