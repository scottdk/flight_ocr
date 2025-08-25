"""
Command-line interface for flight OCR processing.
"""

import argparse
from pathlib import Path

from flight_ocr.core.data_extractor import configure_logging
from flight_ocr.core.flight_grid_processor import FlightGridOCR
from flight_ocr.cli.threshold import add_threshold_parser


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
    ocr_parser.add_argument('--optimal_thresholds_csv', type=str, 
                           default=str(Path.cwd() / "data" / "output" / "results" / "optimal_thresholds.csv"),
                           help='Path to the CSV file with optimal thresholds')
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
    ocr = FlightGridOCR(args.optimal_thresholds_csv, debug=args.debug, output_dir=output_dir, mock_mode=args.mock)
    ocr.process_images()

def main():
    """
    Main entry point for the CLI.
    """
    # Check if the user is using subcommand syntax
    import sys
    
    # If any argument is a known subcommand, use the new parser
    if len(sys.argv) > 1 and any(arg in ['process', 'optimize-thresholds'] for arg in sys.argv[1:]):
        # New subcommand mode
        parser = create_main_parser()
        args = parser.parse_args()
        
        # If no subcommand provided, show help
        if args.command is None:
            parser.print_help()
        else:
            # Execute the chosen subcommand
            args.func(args)
        return

    # Legacy mode - use the old argument parser for backward compatibility
    legacy_parser = argparse.ArgumentParser(
        description="Extract flight grid prices from images using OCR.")
    legacy_parser.add_argument('--debug', action='store_true', help='Enable debug output')
    legacy_parser.add_argument('--optimal-thresholds-csv', type=str, 
                               default=str(Path.cwd() / "data" / "output" / "results" / "optimal_thresholds.csv"),
                               help='Path to the CSV file with optimal thresholds')
    legacy_parser.add_argument('--output-csv', type=str, default="flight_prices.csv",
                               help='Output CSV file name')
    legacy_parser.add_argument('--output-dir', type=str,
                               help='Output directory (defaults to data/output/grid_results)')
    legacy_parser.add_argument('--mock', action='store_true', 
                               help='Use mock OCR data for testing (no tesseract required)')
    
    legacy_args = legacy_parser.parse_args()
    run_ocr_processing(legacy_args)


if __name__ == "__main__":
    main()
