"""
Image preprocessing utilities for OCR processing.
"""

from pathlib import Path
from typing import Optional
from PIL import Image
import pytesseract

# Import cache utilities
from ..utils.cache import get_raw_cache_file, load_from_cache, save_to_cache, get_processed_image_path


class TesseractError(Exception):
    """Custom exception for Tesseract-related errors that can be safely serialized in multiprocessing."""
    
    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


def check_tesseract_installation():
    """
    Check if Tesseract is properly installed and accessible.
    
    Returns:
        tuple: (bool, str) - Success status and message
    """
    try:
        # Try to get Tesseract version
        version = pytesseract.get_tesseract_version()
        return True, f"Tesseract {version} is accessible"
    except pytesseract.TesseractNotFoundError:
        return False, "Tesseract executable not found. Please install Tesseract OCR and ensure it's in your PATH."
    except (ImportError, RuntimeError) as e:
        return False, f"Error checking Tesseract: {e}"


def preprocess_image(image_path: Path, debug: bool = False, threshold: int = 180,
                    output_dir: Optional[Path] = None, no_cache: bool = False) -> Image.Image:
    """
    Preprocess the image: grayscale and fixed thresholding.
    
    Args:
        image_path: Path to the input image
        debug: Whether to save preprocessed image for debugging
        threshold: Threshold value for binarization
        output_dir: Directory to save preprocessed images (for debug)
        no_cache: If True, skip reading from cache but still save to cache
        
    Returns:
        PIL Image: Binarized PIL Image ready for OCR
    """
    # Check cache for preprocessed image first (unless cache read is disabled)
    if not no_cache:
        processed_path_str = get_processed_image_path(image_path, threshold)
        processed_path = Path(processed_path_str)
        if processed_path.exists():
            if debug:
                print(f"✅ Loaded preprocessed image from cache: {processed_path}")
            return Image.open(processed_path)
    
    # Process image
    img = Image.open(image_path)
    img_gray = img.convert('L')
    img_bin = img_gray.point(lambda x: 255 if x > threshold else 0, mode='1')
    
    # Always save to cache after processing (regardless of no_cache setting)
    processed_path_str = get_processed_image_path(image_path, threshold)
    processed_path = Path(processed_path_str)
    processed_path.parent.mkdir(parents=True, exist_ok=True)
    img_bin.save(processed_path)
    if debug:
        print(f"💾 Saved preprocessed image to cache: {processed_path}")
    
    # Also save for debug if requested
    if debug:
        if output_dir is None:
            project_root = Path(__file__).parent.parent.parent
            output_dir = project_root / "data" / "output" / "processed_images"
        
        output_dir.mkdir(parents=True, exist_ok=True)
        debug_path = output_dir / ("_" + image_path.name)
        img_bin.save(debug_path)
        print(f"🐛 Saved debug preprocessed image: {debug_path}")
    
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
        
    Raises:
        TesseractError: If Tesseract is not accessible or encounters an error
    """
    if tess_config is None:
        tess_config = (r'-c tessedit_char_whitelist=A$0123456789,.abcdefghijklmnopqr'
                      r'stuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ :/-–—\' --psm 6 --oem 3')
    
    try:
        ocr_text = pytesseract.image_to_string(img, config=tess_config)
        
        if debug:
            print(f"OCR text:\n{ocr_text}")
        
        return ocr_text
        
    except pytesseract.TesseractNotFoundError as e:
        error_msg = "Tesseract not found. Please install Tesseract OCR and ensure it's in your PATH."
        if debug:
            print(f"❌ OCR Error: {error_msg}")
        raise TesseractError(error_msg) from e
        
    except pytesseract.TesseractError as e:
        error_msg = f"Tesseract processing error: {str(e)}"
        if debug:
            print(f"❌ OCR Error: {error_msg}")
        raise TesseractError(error_msg) from e
        
    except (OSError, RuntimeError) as e:
        if "tesseract" in str(e).lower():
            error_msg = f"Tesseract system error: {str(e)}"
            if debug:
                print(f"❌ OCR Error: {error_msg}")
            raise TesseractError(error_msg) from e
        else:
            # Re-raise other system errors as-is
            raise


def run_ocr_with_cache(image_path: Path, threshold: int, no_cache: bool = False, 
                      debug: bool = False, tess_config: Optional[str] = None,
                      no_preprocess_cache: bool = False) -> str:
    """
    Run OCR with automatic caching support.
    
    This function handles all caching logic internally. It will:
    1. Check cache first (unless no_cache=True)
    2. If not in cache or cache disabled, perform OCR
    3. Save results to cache after OCR (unless no_cache=True)
    
    Args:
        image_path: Path to the input image
        threshold: Threshold value for binarization
        no_cache: If True, skip cache check and don't save to cache
        debug: Whether to print debug information
        tess_config: Tesseract configuration string
        no_preprocess_cache: If True, disable caching for preprocessed images
        
    Returns:
        str: OCR extracted text
        
    Raises:
        TesseractError: If Tesseract is not accessible or encounters an error
    """
    # Get cache file path
    raw_cache_file = get_raw_cache_file(image_path, threshold)
    
    # Check cache first (unless cache disabled)
    if not no_cache:
        cached_ocr_text = load_from_cache(raw_cache_file)
        if cached_ocr_text is not None:
            if debug:
                print(f"✅ Loaded OCR text from cache: {raw_cache_file}")
            return cached_ocr_text
    
    # Perform OCR (cache miss or cache disabled)
    if debug:
        print(f"🔄 {'Computing' if no_cache else 'Computing'} OCR for {image_path} (threshold={threshold})")
    
    # Preprocess image (with caching unless disabled)
    img_bin = preprocess_image(image_path, debug=debug, threshold=threshold, no_cache=no_cache or no_preprocess_cache)
    
    # Run OCR
    ocr_text = run_ocr(img_bin, debug=debug, tess_config=tess_config)
    
    # Save to cache after successful OCR (unless cache disabled)
    if not no_cache:
        save_to_cache(raw_cache_file, ocr_text)
        if debug:
            print(f"💾 Saved OCR text to cache: {raw_cache_file}")
    
    return ocr_text


def process_image_for_ocr(image_path: Path, threshold: int = 180, 
                         no_preprocess: bool = False,
                         no_cache: bool = False, debug: bool = False,
                         tess_config: Optional[str] = None) -> str:
    """
    Single point of access for image processing and OCR.
    
    This is the main function that should be used by threshold_optimizer and flight_grid_processor.
    It handles all preprocessing and caching internally.
    
    Args:
        image_path: Path to the input image
        threshold: Threshold value for binarization (default: 180)
        no_preprocess: If True, skip image preprocessing (use raw image)
        no_cache: If True, disable all caching (both OCR and preprocessed images)
        debug: Whether to print debug information
        tess_config: Tesseract configuration string
        
    Returns:
        str: OCR extracted text
        
    Raises:
        TesseractError: If Tesseract is not accessible or encounters an error
    """
    use_preprocessing = not no_preprocess
    
    if debug:
        print(f"🖼️  Processing {image_path} (threshold={threshold}, cache={not no_cache}, preprocess={use_preprocessing})")
    
    if not use_preprocessing:
        # Skip preprocessing, use raw image
        if debug:
            print("⚠️  Skipping preprocessing, using raw image")
        img = Image.open(image_path)
        ocr_text = run_ocr(img, debug=debug, tess_config=tess_config)
        return ocr_text
    
    if no_cache:
        # Skip all caching, do direct processing
        if debug:
            print("⚠️  Cache disabled, performing direct OCR")
        img_bin = preprocess_image(image_path, debug=debug, threshold=threshold, no_cache=True)
        ocr_text = run_ocr(img_bin, debug=debug, tess_config=tess_config)
        return ocr_text
    
    # Use the cached OCR function for normal processing
    return run_ocr_with_cache(
        image_path=image_path,
        threshold=threshold,
        no_cache=False,
        debug=debug,
        tess_config=tess_config,
        no_preprocess_cache=False
    )
