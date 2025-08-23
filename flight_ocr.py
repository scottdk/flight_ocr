import logging
from pathlib import Path
from PIL import Image
import pytesseract
import csv
from typing import List, Tuple

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

NUM_ROWS = 7
NUM_COLS = 7

class FlightGridOCR:
    """Class to perform OCR on flight grid images and extract price data."""
    def __init__(self, img_dir: Path):
        """Initialize with the directory containing images."""
        self.img_dir = Path(img_dir)
        self.data: List[Tuple[str, str, str]] = []

    def process_images(self) -> None:
        """Process all PNG images in the directory and extract data."""
        for img_file in self.img_dir.glob("*.png"):
            self.data.extend(self.extract_grid_data(img_file))

    def extract_grid_data(self, image_path: Path) -> List[Tuple[str, str, str]]:
        """Extract grid data from a single image file."""
        try:
            img = Image.open(image_path)
        except (OSError, FileNotFoundError) as err:
            logging.error("Error opening image %s: %s", image_path, err)
            return []
        ocr_text = pytesseract.image_to_string(img)
        lines = [line for line in ocr_text.splitlines() if line.strip()]
        from_dates: List[str] = []
        to_dates: List[str] = []
        prices: List[Tuple[str, str, str]] = []
        # Find headers
        for idx, line in enumerate(lines):
            if "From Date" in line:
                from_dates = lines[idx+1].split()
            if "To Date" in line:
                to_dates = [line_item.split()[-1] for line_item in lines[idx+1:idx+NUM_ROWS+1] if line_item.split()]
        # Extract prices
        for row in range(NUM_ROWS):
            if len(lines) > row+2:
                row_line = lines[row+2]
                cells = row_line.split()
                for col in range(NUM_COLS):
                    try:
                        price = cells[col+1]
                        prices.append((from_dates[col], to_dates[row], price))
                    except (IndexError, ValueError):
                        continue
        return prices

    def write_csv(self, output_csv: str) -> None:
        """Write the extracted data to a CSV file."""
        with open(output_csv, "w", newline="", encoding="utf-8") as file:
            writer = csv.writer(file)
            writer.writerow(["From_Date", "To_Date", "Price"])
            for row in self.data:
                writer.writerow(row)
        logging.info("Extracted data written to %s", output_csv)


def main() -> None:
    """Main entry point for the script."""
    img_dir = Path.home() / "Pictures" / "Screenshots" / "flights"
    output_csv = "flight_prices.csv"
    ocr = FlightGridOCR(img_dir)
    ocr.process_images()
    ocr.write_csv(output_csv)

if __name__ == "__main__":
    main()