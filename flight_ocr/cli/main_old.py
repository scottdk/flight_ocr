"""
Command-line interface for flight OCR processing.
"""

import argparse
from pathlib import Path

from ..core.data_extractor import configure_logging
from ..core.ocr_engine import FlightGridOCR


"""
Command-line interface for flight OCR processing.
"""

import argparse
from pathlib import Path

from ..core.data_extractor import configure_logging
from ..core.ocr_engine import FlightGridOCR
from .threshold import add_threshold_parser


def create_main_parser():
    """Create the main argument parser with subcommands."""
    parser = argparse.ArgumentParser(
        prog='flight-ocr',
        description="Extract flight grid prices from images using OCR."
    )
    
    # Global arguments
    parser.add_argument('--debug', action='store_true', help='Enable debug output')
    
    # Create subcommands
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # OCR processing subcommand (default)
    ocr_parser = subparsers.add_parser('process', help='Process images with OCR')
    ocr_parser.add_argument('--img-dir', type=str, 
                           default=str(Path.cwd() / "data" / "input" / "raw"),
                           help='Directory containing images')
    ocr_parser.add_argument('--output-csv', type=str, default="flight_prices.csv",
                           help='Output CSV file name')
    ocr_parser.add_argument('--output-dir', type=str,
                           help='Output directory (defaults to data/output)')
    ocr_parser.add_argument('--mock', action='store_true', 
                           help='Use mock OCR data for testing (no tesseract required)')
    ocr_parser.set_defaults(func=run_ocr_processing)
    
    # Add threshold optimization subcommand
    add_threshold_parser(subparsers)
    
    return parser


def run_ocr_processing(args):
    """Execute OCR processing on images."""
    configure_logging(args.debug)
    
    output_dir = Path(args.output_dir) if args.output_dir else None
    ocr = FlightGridOCR(args.img_dir, debug=args.debug, output_dir=output_dir, mock_mode=args.mock)
    ocr.process_images()
    ocr.write_csv(args.output_csv)


def main():
    """
    Main entry point for the CLI.
    """
    parser = create_main_parser()
    args = parser.parse_args()
    
    # If no subcommand provided, default to OCR processing with legacy arguments
    if args.command is None:
        # For backward compatibility, support the old argument format
        legacy_parser = argparse.ArgumentParser()
        legacy_parser.add_argument('--debug', action='store_true', help='Enable debug output')
        legacy_parser.add_argument('--img-dir', type=str, 
                                   default=str(Path.cwd() / "data" / "input" / "raw"),
                                   help='Directory containing images')
        legacy_parser.add_argument('--output-csv', type=str, default="flight_prices.csv",
                                   help='Output CSV file name')
        legacy_parser.add_argument('--output-dir', type=str,
                                   help='Output directory (defaults to data/output)')
        legacy_parser.add_argument('--mock', action='store_true', 
                                   help='Use mock OCR data for testing (no tesseract required)')
        
        legacy_args = legacy_parser.parse_args()
        run_ocr_processing(legacy_args)
    else:
        # Execute the chosen subcommand
        args.func(args)


if __name__ == "__main__":
    main()
