"""
CLI command for threshold optimization analysis.
"""


from flight_ocr.analysis.threshold_optimizer import batch_process



def add_threshold_parser(subparsers):
    """Add threshold optimization subcommand to argument parser."""
    threshold_parser = subparsers.add_parser(
        'optimize-thresholds', 
        help='Analyze and optimize OCR preprocessing thresholds'
    )
    threshold_parser.add_argument(
        '--no-cache', 
        action='store_true', 
        dest='no_cache',
        help='Disable all caching (default: use cache)'
    )
    threshold_parser.add_argument(
        '--max-workers', 
        type=int, 
        default=4,
        help='Maximum number of worker processes (default: 4)'
    )
    threshold_parser.add_argument(
        '--thresholds', 
        type=str, 
        default='171-173',
        help='Threshold values: single (171), range (171-173), list (171,173), or mixed (171,175,177-179) (default: 171-173)'
    )
    threshold_parser.add_argument(
        '--skip', 
        type=int, 
        default=0,
        help='Number of rows to skip (default: 0)'
    )
    threshold_parser.add_argument(
        '--take', 
        type=int, 
        default=9,
        help='Number of rows to take (default: 9)'
    )
    threshold_parser.add_argument(
        '--image-file', 
        type=str,
        help='Single image file to process (overrides --image-dir)'
    )
    threshold_parser.add_argument(
        '--image-dir',
        type=str,
        default='data/input/raw',
        help='Directory containing images (default: data/input/raw)'
    )
    threshold_parser.set_defaults(func=run_threshold_optimization)


def run_threshold_optimization(args):
    """Execute threshold optimization analysis."""
    print("🔍 Running threshold optimization analysis...")
    batch_process(
        no_cache=args.no_cache, 
        max_workers=args.max_workers,
        thresholds=args.thresholds,
        skip=args.skip,
        take=args.take,
        image_file=args.image_file,
        image_dir=args.image_dir
    )
    print("✅ Threshold analysis complete!")
