"""
Cache utilities for flight OCR processing.
"""

import os
import pickle
from pathlib import Path


def get_cache_file(image_path, threshold, cache_dir=None):
    """
    Generate the cache file path for a given image and threshold.
    Creates the cache directory if it does not exist.

    Args:
        image_path (str or Path): Path to the image file.
        threshold (int): Threshold value used for processing.
        cache_dir (str or Path, optional): Custom cache directory.
                                         Defaults to data/cache/ocr_text.

    Returns:
        str: Path to the cache file.
    """
    if cache_dir is None:
        # Use the new structured cache directory
        project_root = Path(__file__).parent.parent.parent
        cache_dir = project_root / "data" / "cache" / "ocr_text"
    else:
        cache_dir = Path(cache_dir)
    
    cache_dir.mkdir(parents=True, exist_ok=True)
    
    cache_file = cache_dir / f"{Path(image_path).name}_thr{threshold}.pkl"
    return str(cache_file)


def get_raw_cache_file(image_path, threshold):
    """
    Generate cache file path for raw OCR text cache.
    
    Args:
        image_path (str or Path): Path to the image file.
        threshold (int): Threshold value used for processing.
    
    Returns:
        str: Path to the raw cache file.
    """
    project_root = Path(__file__).parent.parent.parent
    cache_dir = project_root / "data" / "cache" / "raw_ocr"
    cache_dir.mkdir(parents=True, exist_ok=True)
    
    image_stem = Path(image_path).stem
    cache_file = cache_dir / f"{image_stem}_{threshold}.pkl"
    return str(cache_file)


def get_processed_image_path(image_path, threshold):
    """
    Generate path for processed/preprocessed image files.
    
    Args:
        image_path (str or Path): Path to the original image file.
        threshold (int): Threshold value used for processing.
        
    Returns:
        str: Path to the processed image file.
    """
    project_root = Path(__file__).parent.parent.parent
    processed_dir = project_root / "data" / "cache" / "processed_images"
    processed_dir.mkdir(parents=True, exist_ok=True)
    
    image_path = Path(image_path)
    processed_file = processed_dir / f"{image_path.stem}_{threshold}{image_path.suffix}"
    return str(processed_file)


def get_raw_ocr_csv_path(image_path, threshold):
    """
    Generate path for raw OCR text CSV files.
    
    Args:
        image_path (str or Path): Path to the original image file.
        threshold (int): Threshold value used for processing.
        
    Returns:
        str: Path to the raw OCR CSV file.
    """
    project_root = Path(__file__).parent.parent.parent
    raw_ocr_dir = project_root / "data" / "cache" / "raw_ocr_text"
    raw_ocr_dir.mkdir(parents=True, exist_ok=True)
    
    image_stem = Path(image_path).stem
    csv_file = raw_ocr_dir / f"th{threshold}_{image_stem}_raw.csv"
    return str(csv_file)


def load_from_cache(cache_file):
    """
    Load data from a cache file if it exists.

    Args:
        cache_file (str): Path to the cache file.

    Returns:
        Any: The data loaded from the cache, or None if not found.
    """
    if os.path.exists(cache_file):
        with open(cache_file, 'rb') as f:
            return pickle.load(f)
    return None


def save_to_cache(cache_file, data):
    """
    Save data to a cache file using pickle.

    Args:
        cache_file (str): Path to the cache file.
        data (Any): Data to be cached.
    """
    cache_path = Path(cache_file)
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(cache_file, 'wb') as f:
        pickle.dump(data, f)
