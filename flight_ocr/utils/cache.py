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
