
"""
flight-ocr.py

Extracts price data from flight grid images using OCR and writes results to a CSV file.

Usage:
    python flight-ocr.py [--debug] [--img-dir IMG_DIR] [--output-csv OUTPUT_CSV]
"""

import logging
import csv
from pathlib import Path
from typing import List, Tuple
from ocr_utils import preprocess_image, run_ocr

def configure_logging(debug: bool = False):
    """
    Configure the logging level and format for the script.
    
    Args:
        debug (bool): If True, set logging to DEBUG level; otherwise INFO.
    """
    level = logging.DEBUG if debug else logging.INFO
    logging.basicConfig(level=level, format='%(levelname)s: %(message)s')

NUM_ROWS = 7
NUM_COLS = 7



class FlightGridOCR:
    """
    Class to perform OCR on flight grid images and extract price data.
    """
    @staticmethod
    def clean_price(value: str) -> str:
        """Remove unwanted symbols (keep A, $, digits, comma, period)."""
        import re
        return re.sub(r'[^A-Za-z0-9$.,]', '', value)

    def __init__(self, img_dir: Path, debug: bool = False):
        """
        Initialize with the directory containing images and debug flag.
        """
        self.img_dir = Path(img_dir)
        self.data: List[Tuple[str, str, str]] = []
        self.debug = debug

    def process_images(self) -> None:
        """
        Process all PNG images in the directory, ignoring files with an underscore prefix.
        """
        img_files = [f for f in self.img_dir.glob("*.png") if not f.name.startswith("_")]
        if self.debug:
            logging.debug(f"Image directory: {self.img_dir}")
            logging.debug(f"Found image files: {img_files}")
        for img_file in img_files:
            if self.debug:
                logging.debug(f"Processing image: {img_file}")
            self.data.extend(self.extract_grid_data(img_file))

    def extract_grid_data(self, image_path: Path) -> List[Tuple[str, str, str]]:
        """
        Extract grid data from a single image file, using vertical strips per column.
        """
        import re
        try:
            img_bin = preprocess_image(image_path, debug=self.debug)
        except (OSError, FileNotFoundError) as err:
            logging.error(f"Error opening image {image_path}: {err}")
            return []
        tess_config = r'-c tessedit_char_whitelist=A$0123456789,.abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ :/-–—\' --psm 6 --oem 3'
        ocr_text = run_ocr(img_bin, debug=self.debug, tess_config=tess_config)
        price_pattern = re.compile(r'^(A\$|\$)?[0-9][0-9,]*[.,][0-9]{2,3}$')
        lines = [line.strip() for line in ocr_text.splitlines() if line.strip()]
        if self.debug:
            logging.debug(f"Parsed non-empty lines ({len(lines)}): {lines}")

        prices: List[Tuple[str, str, str]] = []
        all_columns = []
        col = 1
        i = 0
        # Process first 7 columns as blocks of 9 lines
        while i + 9 <= len(lines) and col <= 7:
            day_of_week = lines[i]
            date_header = lines[i+1]
            price_cells_raw = lines[i+2:i+9]
            price_cells = [val for val in price_cells_raw if price_pattern.match(val)]
            if self.debug:
                logging.debug(f"Column {col}: day={day_of_week}, date={date_header}, prices={price_cells}")
            all_columns.append((date_header, price_cells))
            col += 1
            i += 9

        # Remaining lines are column 8 (row headers: alternating day/date)
        col8_values = lines[i:]
        if self.debug:
            logging.debug(f"Column 8 (row header) values: {col8_values}")

        # Extract only the date values: skip the first value, then take every second value
        row_headers = [val for idx, val in enumerate(col8_values) if idx % 2 == 1]
        if len(row_headers) < 7:
            row_headers = col8_values

        for col_idx, (date_header, price_cells) in enumerate(all_columns):
            for row, price in enumerate(price_cells, start=1):
                to_date = row_headers[row-1] if row-1 < len(row_headers) else ''
                price = self.clean_price(price)
                prices.append((date_header, to_date, price))
        return prices

    def write_csv(self, output_csv: str) -> None:
        """
        Write the extracted data to a CSV file.
        """
        with open(output_csv, "w", newline="", encoding="utf-8") as file:
            writer = csv.writer(file)
            writer.writerow(["From_Date", "To_Date", "Price"])
            for row in self.data:
                writer.writerow(row)
        logging.info(f"Extracted data written to {output_csv}")




def main():
    """
    Main entry point for the script.
    """
    import argparse
    parser = argparse.ArgumentParser(description="Extract flight grid prices from images using OCR.")
    parser.add_argument('--debug', action='store_true', help='Enable debug output')
    parser.add_argument('--img-dir', type=str, default=str(Path.cwd() / "images"), help='Directory containing images')
    parser.add_argument('--output-csv', type=str, default="flight_prices.csv", help='Output CSV file name')
    args = parser.parse_args()

    configure_logging(args.debug)
    ocr = FlightGridOCR(args.img_dir, debug=args.debug)
    ocr.process_images()
    ocr.write_csv(args.output_csv)

if __name__ == "__main__":
    main()