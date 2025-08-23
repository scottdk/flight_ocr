
import os
import pickle

def get_cache_file(image_path, threshold):
    """
    Generate the cache file path for a given image and threshold.
    Creates the .cache directory if it does not exist.

    Args:
        image_path (str or Path): Path to the image file.
        threshold (int): Threshold value used for processing.

    Returns:
        str: Path to the cache file.
    """
    cache_dir = os.path.join(os.path.dirname(str(image_path)), '.cache')
    os.makedirs(cache_dir, exist_ok=True)
    cache_file = os.path.join(
        cache_dir,
        f"{os.path.basename(str(image_path))}_thr{threshold}.pkl"
    )
    return cache_file

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
    with open(cache_file, 'wb') as f:
        pickle.dump(data, f)