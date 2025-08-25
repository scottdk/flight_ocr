"""
Image preprocessing utilities for OCR processing.
"""

from pathlib import Path
from typing import Optional
from PIL import Image
import pytesseract
import csv
import os
# Import cache utilities
from ..utils.cache import get_processed_image_path, get_raw_ocr_csv_path
from ..utils.cleaning import clean_lines


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
        error_msg = (
            "Tesseract executable not found. Please:\n"
            "1. Install Tesseract OCR from: https://github.com/UB-Mannheim/tesseract/wiki\n"
            "2. Add Tesseract to your system PATH\n"
            "3. Restart your terminal/IDE after installation"
        )
        return False, error_msg
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
    processed_path_str = get_processed_image_path(image_path, threshold)
    processed_path = Path(processed_path_str)
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
    # original_basename = image_path.stem
    # ext = image_path.suffix.lstrip('.')
    # processed_filename = f"{original_basename}_th{threshold}_processed.{ext}"
    # processed_path = Path(processed_path.parent) / processed_filename
    # processed_path.parent.mkdir(parents=True, exist_ok=True)
    img_bin.save(processed_path)
    if debug:
        print(f"💾 Saved preprocessed image to cache: {processed_path}")
    
    return img_bin


def run_ocr(img: Image.Image, image_path: Path, threshold: int,
           debug: bool = False, tess_config: Optional[str] = None) -> str:
    """
    Run Tesseract OCR on a PIL Image and automatically create CSV output for threshold analysis.
    
    Args:
        img: PIL Image to process
        image_path: Original image path (for CSV filename generation)
        threshold: Threshold value used (for CSV filename generation)
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
        error_msg = (
            "Tesseract not found. Please:\n"
            "1. Install Tesseract OCR from: https://github.com/UB-Mannheim/tesseract/wiki\n"
            "2. Add Tesseract to your system PATH\n"
            "3. Restart your terminal/IDE after installation"
        )
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


def _save_raw_ocr_to_csv_cache(ocr_text: str, csv_path: str, debug: bool = False):
    """
    Save raw OCR text to CSV cache file (no line numbers, no cleaning).
    
    Args:
        ocr_text: The raw OCR text output from Tesseract
        csv_path: Path to the CSV cache file
        debug: Whether to print debug information
    """
    csv_file = Path(csv_path)
    csv_file.parent.mkdir(parents=True, exist_ok=True)
    
    with open(csv_file, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.writer(csvfile)
        
        # Write header for raw cache format
        writer.writerow(['ocr_text'])
        
        # Write raw OCR text as single field (preserve all newlines)
        writer.writerow([ocr_text])
    
    if debug:
        print(f"� Saved raw OCR to CSV cache: {csv_path}")


def _load_from_csv_cache(csv_path: str) -> Optional[str]:
    """
    Load raw OCR text from a CSV cache file.
    
    Args:
        csv_path: Path to the CSV cache file
        
    Returns:
        str: Raw OCR text if found, None if file doesn't exist or is invalid
    """
    csv_file = Path(csv_path)
    if not csv_file.exists():
        return None
    
    try:
        with open(csv_file, 'r', newline='', encoding='utf-8') as csvfile:
            reader = csv.reader(csvfile)
            header = next(reader, None)  # Skip header
            if header != ['ocr_text']:
                return None  # Invalid format
            
            # Read the raw OCR text (should be single row)
            row = next(reader, None)
            if row and len(row) >= 1:
                return row[0]  # Raw OCR text is in first column
        
        return None
    except (IOError, csv.Error):
        return None


def _create_cleaned_ocr_csv(raw_ocr_text: str, image_path: Path, threshold: int, debug: bool = False) -> list:
    """
    Create cleaned OCR CSV files with line numbers and return cleaned lines.
    
    Args:
        raw_ocr_text: The raw OCR text from Tesseract
        image_path: Original image path  
        threshold: Threshold value used
        debug: Whether to print debug information
        
    Returns:
        list: Cleaned lines from OCR text
    """
    # Split raw text into lines
    raw_lines = raw_ocr_text.split('\n')
    
    # Apply cleaning
    cleaned_lines, _ = clean_lines(raw_lines)
    
    # Create output directories
    project_root = Path(__file__).parent.parent.parent
    csv_dir = project_root / "data" / "output" / "raw_ocr_csv"
    cleaned_dir = project_root / "data" / "output" / "cleaned"
    csv_dir.mkdir(parents=True, exist_ok=True)
    cleaned_dir.mkdir(parents=True, exist_ok=True)
    
    # Generate filenames
    image_stem = image_path.stem
    csv_filename = f"{image_stem}_th{threshold}_raw.csv"
    cleaned_filename = f"{image_stem}_th{threshold}_cleaned.csv"
    # Save CSV with line numbers (raw_ocr_csv directory)
    csv_path = csv_dir / csv_filename
    with open(csv_path, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(['line_number', 'ocr_text'])
        for i, line in enumerate(cleaned_lines, start=1):
            writer.writerow([i, line])
    # Save cleaned data (cleaned directory)
    cleaned_path = cleaned_dir / cleaned_filename
    with open(cleaned_path, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(['line_number', 'cleaned_text'])
        for i, line in enumerate(cleaned_lines, start=1):
            writer.writerow([i, line])
    if debug:
        print(f"📄 Saved cleaned OCR CSV with {len(cleaned_lines)} lines: {csv_path}")
        print(f"📄 Saved cleaned data: {cleaned_path}")
    return cleaned_lines, cleaned_path


def process_image_for_ocr(image_path: Path, threshold: int = 180, 
                         no_preprocess: bool = False,
                         no_cache: bool = False, debug: bool = False,
                         tess_config: Optional[str] = None) -> list:
    """
    Single point of access for image processing and OCR with automatic CSV generation.
    
    This function handles all preprocessing, OCR, caching, and CSV generation internally.
    It will automatically create a CSV file in data/output/raw_ocr_csv/ for threshold analysis.
    
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
    if debug:
        print(f"🖼️  Processing {image_path} (threshold={threshold}, cache={not no_cache}, preprocess={not no_preprocess})")
    
    # Handle caching logic using CSV files
    cache_csv_path = get_raw_ocr_csv_path(image_path, threshold)
    processed_image_path = get_processed_image_path(image_path, threshold)
    
    # Handle no preprocessing case
    if no_preprocess:
        if debug:
            print("⚠️  Skipping preprocessing, using raw image")
        img = Image.open(image_path)
        raw_ocr_text = run_ocr(img, image_path, threshold, debug=debug, tess_config=tess_config)
        cleaned_lines, clean_csv = _create_cleaned_ocr_csv(raw_ocr_text, image_path, threshold, debug=debug)
        return [(image_path, threshold, cleaned_lines, clean_csv, cache_csv_path, processed_image_path)]


    # Check cache first (unless cache disabled)
    if not no_cache:
        cached_ocr_text = _load_from_csv_cache(cache_csv_path)
        if cached_ocr_text is not None:
            if debug:
                print(f"✅ Loaded OCR text from CSV cache: {cache_csv_path}")
            # Create cleaned CSV files from cached raw text
            cleaned_lines, clean_csv = _create_cleaned_ocr_csv(cached_ocr_text, image_path, threshold, debug=debug)
            return [(image_path, threshold, cleaned_lines, clean_csv, cache_csv_path, processed_image_path)]
    
    # Process image and run OCR
    if debug:
        print(f"� Computing OCR for {image_path} (threshold={threshold})")
    
    # Preprocess image (with caching unless disabled)
    img_bin = preprocess_image(image_path, debug=debug, threshold=threshold, no_cache=no_cache)
    
    # Run OCR to get raw text
    raw_ocr_text = run_ocr(img_bin, image_path, threshold, debug=debug, tess_config=tess_config)
    
    # Save to CSV cache after successful OCR (unless cache disabled)
    if not no_cache:
        _save_raw_ocr_to_csv_cache(raw_ocr_text, cache_csv_path, debug=debug)
    
    # Create cleaned CSV files and return cleaned lines
    cleaned_lines, clean_csv  = _create_cleaned_ocr_csv(raw_ocr_text, image_path, threshold, debug=debug)
    return [(image_path, threshold, cleaned_lines, clean_csv, cache_csv_path, processed_image_path)]


def batch_process_images_for_ocr(image_paths, thresholds, max_workers=4, 
                                no_preprocess=False, no_cache=False, 
                                debug=False, tess_config=None, progress_callback=None):
    """
    Process multiple images with multiple thresholds using multiprocessing.
    
    This function handles all multithreading for OCR processing, keeping 
    threshold_optimizer agnostic to threading implementation.
    
    Args:
        image_paths: List or set of Path objects for images to process
        thresholds: List of threshold values to test
        max_workers: Maximum number of worker processes
        no_preprocess: If True, skip image preprocessing
        no_cache: If True, disable all caching
        debug: Whether to print debug information
        tess_config: Tesseract configuration string
        progress_callback: Optional callback function to report progress: callback(current, total, image_path, threshold)
        
    Returns:
        List of tuples: [(image_path, threshold, ocr_text, success, error_msg), ...]
        
    Raises:
        TesseractError: If Tesseract is not accessible or encounters an error
    """
    import concurrent.futures
    from functools import partial
    
    # Create all combinations of image_path and threshold
    tasks = [(image_path, threshold) 
             for image_path in image_paths 
             for threshold in thresholds]
    
    results = []
    
    # Create partial function with fixed parameters
    process_func = partial(
        _process_single_image_task,
        no_preprocess=no_preprocess,
        no_cache=no_cache,
        debug=debug,
        tess_config=tess_config
    )
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Submit all tasks
        future_to_task = {
            executor.submit(process_func, task): task 
            for task in tasks
        }
        
        # Collect results as they complete with progress reporting
        completed = 0
        total_tasks = len(tasks)
        for future in concurrent.futures.as_completed(future_to_task):
            task = future_to_task[future]
            image_path, threshold = task
            completed += 1
            
            # Report progress if callback provided
            if progress_callback:
                progress_callback(completed, total_tasks, image_path, threshold)
            
            try:
                result = future.result()
                results.append(result)
            except Exception as exc:
                error_result = (image_path, threshold, "", False, str(exc))
                results.append(error_result)
    
    return results


def _process_single_image_task(task, no_preprocess=False, no_cache=False, 
                              debug=False, tess_config=None):
    """
    Process a single image-threshold combination task.
    
    This is a separate function to support multiprocessing serialization.
    
    Args:
        task: Tuple of (image_path, threshold)
        no_preprocess: If True, skip image preprocessing
        no_cache: If True, disable all caching
        debug: Whether to print debug information
        tess_config: Tesseract configuration string
        
    Returns:
        Tuple: (image_path, threshold, ocr_text, success, error_msg)
    """
    image_path, threshold = task
    
    try:
        result_list = process_image_for_ocr(
            image_path=image_path,
            threshold=threshold,
            no_preprocess=no_preprocess,
            no_cache=no_cache,
            debug=debug,
            tess_config=tess_config
        )
        # Extract cleaned lines from the first (and only) result tuple
        _, _, cleaned_lines, cleaned_path, raw_path, processed_path = result_list[0]
        ocr_text = '\n'.join(cleaned_lines)
        return (image_path, threshold, ocr_text, True, "", cleaned_path, raw_path, processed_path)

    except TesseractError as e:
        return (image_path, threshold, "", False, e.message, "")
    except Exception as e:
        return (image_path, threshold, "", False, str(e), "")


