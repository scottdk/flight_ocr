"""
ocr_utils.py

Utility functions for image preprocessing and OCR.
"""


from pathlib import Path
from typing import Optional
from PIL import Image, ImageEnhance, ImageFilter
import numpy as np
import pytesseract

def preprocess_image(image_path: Path, debug: bool = False, threshold: int = 180) -> Image.Image:
    """
    Preprocess the image: grayscale and fixed thresholding.
    Returns a binarized PIL Image.
    """
    img = Image.open(image_path)
    img_gray = img.convert('L')
    img_bin = img_gray.point(lambda x: 255 if x > threshold else 0, mode='1')
    if debug:
        preprocessed_path = image_path.parent / ("_" + image_path.name)
        img_bin.save(preprocessed_path)
        print(f"Saved preprocessed image as {preprocessed_path}")
    return img_bin

    # No longer needed for simple thresholding

def run_ocr(img: Image.Image, debug: bool = False, tess_config: Optional[str] = None) -> str:
    """
    Run Tesseract OCR on a PIL Image with optional config.
    """
    if tess_config is None:
        tess_config = r'-c tessedit_char_whitelist=A$0123456789,.abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ :/-–—\' --psm 6 --oem 3'
    ocr_text = pytesseract.image_to_string(img, config=tess_config)
    if debug:
        print(f"OCR text:\n{ocr_text}")
    return ocr_text
