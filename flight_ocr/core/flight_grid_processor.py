"""
Flight grid processing module for extracting flight price data from images.
"""

import csv
from datetime import datetime
from pathlib import Path
import logging
from typing import List, Tuple

from ..core.image_processor import process_image_for_ocr
from ..utils.cache import get_cache_file, load_from_cache, save_to_cache
from ..utils.cleaning import clean_lines
from ..utils.file_io import write_csv_data
from ..utils.mock_ocr import mock_ocr_text
from shutil import copy2
from datetime import date


# Constants
NUM_ROWS = 7
NUM_COLS = 7
THRESHOLD = 173


class FlightGridOCR:
    def add_days_between_dates_column(self):
        """
        Adds a days-between-dates column to self.data, updating each tuple to include the days difference between From_Date and To_Date as an integer (or empty string if not parseable).
        The new self.data will be a list of 4-tuples: (From_Date, To_Date, Price, Days_Between).
        """
        updated_data = []
        for from_date, to_date, price in self.data:
            from_dt = self._parse_mmmdd_to_date(from_date)
            to_dt = self._parse_mmmdd_to_date(to_date)
            if from_dt and to_dt:
                days_between = (to_dt - from_dt).days
            else:
                days_between = ""
            updated_data.append((from_date, to_date, price, days_between))
        self.data = updated_data


    def _format_data_dates(self):
        """
        Convert From_Date and To_Date in self.data to ISO date strings if possible.
        """
        converted_data = []
        for from_date, to_date, price in self.data:
            from_dt = self._parse_mmmdd_to_date(from_date)
            to_dt = self._parse_mmmdd_to_date(to_date)
            converted_data.append((
                from_dt.isoformat() if from_dt else from_date,
                to_dt.isoformat() if to_dt else to_date,
                price
            ))
        self.data = converted_data

    def _parse_mmmdd_to_date(self, mmmdd: str) -> date:
        """
        Convert a string in 'MmmD' format (e.g., 'Apr5', 'Dec25') to a date object.
        If the date is more than 31 days in the past, use next year.
        """
        if not mmmdd:
            return None
        try:
            today = date.today()
            # Split month and day
            month_str = mmmdd[:3]
            day_str = mmmdd[3:]
            month = datetime.strptime(month_str, "%b").month
            day = int(day_str)
            year = today.year
            dt = date(year, month, day)
            # If more than 31 days in the past, use next year
            if (today - dt).days > 31:
                dt = date(year + 1, month, day)
            return dt
        except Exception as e:
            logging.warning(f"Could not parse date from '{mmmdd}': {e}")
            return None
    """
    Class to perform OCR on flight grid images and extract price data.
    """

    def __init__(self, optimal_thresholds_csv: str, debug: bool = False, output_dir: Path = None, mock_mode: bool = False):
        """
        Initialize with the directory containing images and debug flag.
        
        Args:
            optimal_thresholds_csv: Path to the CSV file with optimal thresholds
            debug: Enable debug logging
            output_dir: Directory for output files (optional)  
            mock_mode: Use mock OCR data instead of real tesseract (for testing)
        """
        self.optimal_thresholds_csv = Path(optimal_thresholds_csv)
        self.data: List[Tuple[str, str, str]] = []
        self.debug = debug
        self.mock_mode = mock_mode
        
        if output_dir is None:
            # Default to structured output directory
            project_root = Path(__file__).parent.parent.parent
            self.output_dir = project_root / "data" / "output" / "grid_results"
        else:
            self.output_dir = Path(output_dir)

    def process_images(self, optimal_thresholds_csv: str = None) -> None:
        """
        Process images based on an optimal_thresholds CSV file.
        For each file_path in the CSV, read the file and use its second column as ocr_text.
        """
        if optimal_thresholds_csv is None:
            optimal_thresholds_csv = str(Path("data/output/results/optimal_thresholds.csv"))

        self.output_dir = self.package_related_files(optimal_thresholds_csv)

        with open(optimal_thresholds_csv, newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                ocr_file = self.output_dir / Path(row.get('clean_data', '')).name
                with open(ocr_file, newline='', encoding='utf-8') as ocr_f:
                    ocr_reader = csv.DictReader(ocr_f)
                    cleaned_text = [row['cleaned_text'] for row in ocr_reader]
                    # ocr_text = '\n'.join(cleaned_text)
                    self.data.extend(self.extract_grid_data(cleaned_text))
        
        self._format_data_dates()
        
        # self.add_days_between_dates_column()
        
        self.write_csv(self.output_dir / "flight_prices.csv")  
        
    def package_related_files(self, optimal_thresholds_csv: str = None) -> Path: 
        """
        Create an output subfolder and gather the related files listed in optimal_thresholds.
        Returns the path to the created folder.
        """
        # Create output subfolder with timestamp if it doesn't exist
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_subfolder = self.output_dir / f"{timestamp}_related_files"
        output_subfolder.mkdir(parents=True, exist_ok=True)
        
        with open(optimal_thresholds_csv, newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                # Copy the related files to the output subfolder
                for key in ['raw_data', 'clean_data', 'original_image', 'processed_image']:
                    src = row[key]
                    dst = output_subfolder / Path(src).name
                    dst.parent.mkdir(parents=True, exist_ok=True)
                    if Path(src).exists():
                        copy2(src, dst)
                        logging.info("Copied %s to %s", src, dst)
                    copy2(optimal_thresholds_csv, output_subfolder / Path(optimal_thresholds_csv).name)

        return output_subfolder

    def extract_grid_data(self, ocr_text: list) -> List[Tuple[str, str, str]]:
        """
        Extract grid data from OCR text (no longer reads image files).
        """
        # lines = [line.strip() for line in ocr_text.splitlines() if line.strip()]
        
        lines = ocr_text
        
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
        Write the extracted data to a CSV file (no timestamp).
        
        Args:
            output_filename: Name of the output CSV file
        """
        output_path = self.output_dir / output_filename
        # Determine columns based on tuple length, or default if no data
        if self.data:
            if len(self.data[0]) == 4:
                columns = ["From_Date", "To_Date", "Price", "Days_Between"]
            else:
                columns = ["From_Date", "To_Date", "Price"]
        else:
            columns = ["From_Date", "To_Date", "Price"]
        write_csv_data(output_path, self.data, columns)
        logging.info("Extracted data written to %s", output_path)

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
            tess_config = (r'-c tessedict_char_whitelist=A$0123456789,.abcdefghijklmnopqr'
                          r'stuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ :/-–—\' --psm 6 --oem 3')
            ocr_text = process_image_for_ocr(
                image_path=Path(image_path), 
                threshold=threshold,
                debug=self.debug, 
                tess_config=tess_config
            )
            save_to_cache(cache_file, ocr_text)
            return ocr_text
        except (OSError, FileNotFoundError) as err:
            logging.error("Error opening image %s: %s", image_path, err)
            return ""  # Return empty string instead of empty list
