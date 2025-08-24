"""
Image preprocessing utilities for OCR processing.
"""

from pathlib import Path
from typing import Optional
from PIL import Image
import pytesseract


def preprocess_image(image_path: Path, debug: bool = False, threshold: int = 180,
                    output_dir: Optional[Path] = None) -> Image.Image:
    """
    Preprocess the image: grayscale and fixed thresholding.
    
    Args:
        image_path: Path to the input image
        debug: Whether to save preprocessed image for debugging
        threshold: Threshold value for binarization
        output_dir: Directory to save preprocessed images (for debug)
        
    Returns:
        PIL Image: Binarized PIL Image ready for OCR
    """
    img = Image.open(image_path)
    img_gray = img.convert('L')
    img_bin = img_gray.point(lambda x: 255 if x > threshold else 0, mode='1')
    
    if debug:
        if output_dir is None:
            # Use the new structured output directory
            project_root = Path(__file__).parent.parent.parent
            output_dir = project_root / "data" / "output" / "processed_images"
        
        output_dir.mkdir(parents=True, exist_ok=True)
        preprocessed_path = output_dir / ("_" + image_path.name)
        img_bin.save(preprocessed_path)
        print(f"Saved preprocessed image as {preprocessed_path}")
    
    return img_bin


def run_ocr(img: Image.Image, debug: bool = False, 
           tess_config: Optional[str] = None) -> str:
    """
    Run Tesseract OCR on a PIL Image with optional config.
    
    Args:
        img: PIL Image to process
        debug: Whether to print debug information
        tess_config: Tesseract configuration string
        
    Returns:
        str: OCR extracted text
    """
    if tess_config is None:
        tess_config = (r'-c tessedit_char_whitelist=A$0123456789,.abcdefghijklmnopqr'
                      r'stuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ :/-–—\' --psm 6 --oem 3')
    
    ocr_text = pytesseract.image_to_string(img, config=tess_config)
    
    if debug:
        print(f"OCR text:\n{ocr_text}")
    
    return ocr_text
