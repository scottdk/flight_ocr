
"""
flight-ocr.py

Extracts price data from flight grid images using OCR and writes results to a CSV file.

Usage:
    python flight-ocr.py [--debug] [--img-dir IMG_DIR] [--output-csv OUTPUT_CSV]
"""

import logging
from pathlib import Path
import csv
from typing import List, Tuple
from PIL import Image
import pytesseract

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
    """Class to perform OCR on flight grid images and extract price data."""
    def __init__(self, img_dir: Path, debug: bool = False):
        """Initialize with the directory containing images and debug flag."""
        self.img_dir = Path(img_dir)
        self.data: List[Tuple[str, str, str]] = []
        self.debug = debug

    def process_images(self) -> None:
        """Process all PNG images in the directory and extract data."""
        for img_file in self.img_dir.glob("*.png"):
            if self.debug:
                logging.debug(f"Processing image: {img_file}")
            self.data.extend(self.extract_grid_data(img_file))

    def extract_grid_data(self, image_path: Path) -> List[Tuple[str, str, str]]:
        """Extract grid data from a single image file, inferring headers and prices by position."""
        try:
            img = Image.open(image_path)
        except (OSError, FileNotFoundError) as err:
            logging.error("Error opening image %s: %s", image_path, err)
            return []
        ocr_text = pytesseract.image_to_string(img)
        if self.debug:
            logging.debug(f"OCR text for {image_path}: {ocr_text}")
        # Remove empty lines and group lines into logical rows
        lines = [line.strip() for line in ocr_text.splitlines() if line.strip()]
        # Heuristic: group lines into blocks of 8 (day, date, 7 prices)
        prices: List[Tuple[str, str, str]] = []
        i = 0
        while i + 8 <= len(lines):
            day = lines[i]
            date = lines[i+1]
            price_cells = lines[i+2:i+9]
            if self.debug:
                logging.debug(f"Row: day={day}, date={date}, prices={price_cells}")
            for col, price in enumerate(price_cells):
                prices.append((date, f"col{col+1}", price))
            i += 8
        return prices

    def write_csv(self, output_csv: str) -> None:
        """Write the extracted data to a CSV file."""
        with open(output_csv, "w", newline="", encoding="utf-8") as file:
            writer = csv.writer(file)
            writer.writerow(["From_Date", "To_Date", "Price"])
            for row in self.data:
                writer.writerow(row)
        logging.info("Extracted data written to %s", output_csv)



def main():
    """Main entry point for the script."""
    import argparse
    parser = argparse.ArgumentParser(description="Extract flight grid prices from images using OCR.")
    parser.add_argument('--debug', action='store_true', help='Enable debug output')
    parser.add_argument('--img-dir', type=str, default=str(Path.home() / "Pictures" / "Screenshots" / "flights"), help='Directory containing images')
    parser.add_argument('--output-csv', type=str, default="flight_prices.csv", help='Output CSV file name')
    args = parser.parse_args()

    configure_logging(args.debug)
    ocr = FlightGridOCR(args.img_dir, debug=args.debug)
    ocr.process_images()
    ocr.write_csv(args.output_csv)

if __name__ == "__main__":
    main()