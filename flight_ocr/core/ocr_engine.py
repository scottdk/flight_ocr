"""
Main OCR engine for flight grid processing.
"""

import logging
from pathlib import Path
from typing import List, Tuple

from ..core.image_processor import preprocess_image, run_ocr
from ..utils.cache import get_cache_file, load_from_cache, save_to_cache
from ..utils.cleaning import clean_lines
from ..utils.file_io import write_csv_data
from ..utils.mock_ocr import mock_ocr_text


# Constants
NUM_ROWS = 7
NUM_COLS = 7
THRESHOLD = 173


class FlightGridOCR:
    """
    Class to perform OCR on flight grid images and extract price data.
    """

    def __init__(self, img_dir: Path, debug: bool = False, output_dir: Path = None, mock_mode: bool = False):
        """
        Initialize with the directory containing images and debug flag.
        
        Args:
            img_dir: Directory containing input images
            debug: Enable debug logging
            output_dir: Directory for output files (optional)  
            mock_mode: Use mock OCR data instead of real tesseract (for testing)
        """
        self.img_dir = Path(img_dir)
        self.data: List[Tuple[str, str, str]] = []
        self.debug = debug
        self.mock_mode = mock_mode
        
        if output_dir is None:
            # Default to structured output directory
            project_root = Path(__file__).parent.parent.parent
            self.output_dir = project_root / "data" / "output"
        else:
            self.output_dir = Path(output_dir)

    def process_images(self) -> None:
        """
        Process all PNG images in the directory, ignoring files with an underscore prefix.
        """
        img_files = [f for f in self.img_dir.glob("*.png") if not f.name.startswith("_")]
        if self.debug:
            logging.debug("Image directory: %s", self.img_dir)
            logging.debug("Found image files: %s", img_files)
        for img_file in img_files:
            if self.debug:
                logging.debug("Processing image: %s", img_file)
            self.data.extend(self.extract_grid_data(img_file))

    def extract_with_ocr(self, image_path, threshold=THRESHOLD):
        """
        Extract OCR text from an image file, with optional mock mode for testing.
        This method is used to extract data from images with OCR.
        """
        # Use mock data if mock mode is enabled
        if self.mock_mode:
            if self.debug:
                logging.debug("Using mock OCR data for image: %s", image_path)
            return mock_ocr_text()
        
        cache_file = get_cache_file(image_path, threshold)
        cached = load_from_cache(cache_file)
        if cached is not None:
            if self.debug:
                logging.debug("Loaded grid data from cache: %s", cache_file)
            return cached

        try:
            img_bin = preprocess_image(image_path, debug=self.debug, threshold=threshold)
            tess_config = (r'-c tessedict_char_whitelist=A$0123456789,.abcdefghijklmnopqr'
                          r'stuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ :/-–—\' --psm 6 --oem 3')
            ocr_text = run_ocr(img_bin, debug=self.debug, tess_config=tess_config)
            save_to_cache(cache_file, ocr_text)
            return ocr_text
        except (OSError, FileNotFoundError) as err:
            logging.error("Error opening image %s: %s", image_path, err)
            return ""  # Return empty string instead of empty list

    def extract_grid_data(self, image_path: Path) -> List[Tuple[str, str, str]]:
        """
        Extract grid data from a single image file, using vertical strips per column.
        """
        ocr_text = self.extract_with_ocr(image_path, threshold=THRESHOLD)

        lines = [line.strip() for line in ocr_text.splitlines() if line.strip()]
        if self.debug:
            logging.debug("Parsed non-empty lines (%d): %s", len(lines), lines)

        all_columns = self._parse_price_columns(lines)
        row_headers = self._extract_row_headers(lines[63:])  # Remaining lines after 7*9=63

        return self._build_price_tuples(all_columns, row_headers)

    def _parse_price_columns(self, lines: List[str]) -> List[Tuple[str, List[str]]]:
        """Parse the first 7 columns of price data from OCR lines."""
        all_columns = []
        col = 1
        i = 0
        # Process first 7 columns as blocks of 9 lines
        while i + 9 <= len(lines) and col <= 7:
            day_of_week = lines[i]
            date_header = lines[i+1]
            price_cells_raw = lines[i+2:i+9]
            price_cells, price_pattern = clean_lines(price_cells_raw)
            price_cells = [val for val in price_cells if price_pattern.match(val)]
            if self.debug:
                logging.debug("Column %d: day=%s, date=%s, prices=%s",
                            col, day_of_week, date_header, price_cells)
            all_columns.append((date_header, price_cells))
            col += 1
            i += 9
        return all_columns

    def _extract_row_headers(self, col8_values: List[str]) -> List[str]:
        """Extract row headers from column 8 values."""
        if self.debug:
            logging.debug("Column 8 (row header) values: %s", col8_values)

        # Extract only the date values: skip the first value, then take every second value
        row_headers = [val for idx, val in enumerate(col8_values) if idx % 2 == 1]
        if len(row_headers) < 7:
            row_headers = col8_values
        return row_headers

    def _build_price_tuples(self, all_columns: List[Tuple[str, List[str]]],
                           row_headers: List[str]) -> List[Tuple[str, str, str]]:
        """Build price tuples from column data and row headers."""
        prices: List[Tuple[str, str, str]] = []
        for _, (date_header, price_cells) in enumerate(all_columns):
            for row, price in enumerate(price_cells, start=1):
                to_date = row_headers[row-1] if row-1 < len(row_headers) else ''
                prices.append((date_header, to_date, price))
        return prices

    def write_csv(self, output_filename: str = "flight_prices.csv") -> None:
        """
        Write the extracted data to a CSV file.
        
        Args:
            output_filename: Name of the output CSV file
        """
        output_path = self.output_dir / "csv" / output_filename
        write_csv_data(output_path, self.data, ["From_Date", "To_Date", "Price"])
        logging.info("Extracted data written to %s", output_path)
