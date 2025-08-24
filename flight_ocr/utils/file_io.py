"""
File I/O utilities for flight OCR processing.
"""

import csv
import logging
from pathlib import Path
from typing import List, Tuple


def write_csv_data(output_path: Path, data: List[Tuple[str, str, str]], 
                   headers: List[str]) -> None:
    """
    Write data to a CSV file with proper error handling.
    
    Args:
        output_path: Path to the output CSV file
        data: List of data tuples to write
        headers: Column headers for the CSV
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    try:
        with open(output_path, "w", newline="", encoding="utf-8") as file:
            writer = csv.writer(file)
            writer.writerow(headers)
            for row in data:
                writer.writerow(row)
    except (IOError, OSError) as err:
        logging.error("Failed to write CSV file %s: %s", output_path, err)
        raise


def ensure_directory_exists(directory: Path) -> None:
    """
    Ensure a directory exists, creating it if necessary.
    
    Args:
        directory: Path to the directory to create
    """
    directory.mkdir(parents=True, exist_ok=True)
