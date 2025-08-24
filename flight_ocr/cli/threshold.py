"""
CLI command for threshold optimization analysis.
"""

from ..analysis.threshold_optimizer import batch_process


def add_threshold_parser(subparsers):
    """Add threshold optimization subcommand to argument parser."""
    threshold_parser = subparsers.add_parser(
        'optimize-thresholds', 
        help='Analyze and optimize OCR preprocessing thresholds'
    )
    threshold_parser.add_argument(
        '--no-refresh-cache', 
        action='store_false', 
        dest='refresh_cache',
        help='Use cache if available (default: recompute and overwrite)'
    )
    threshold_parser.add_argument(
        '--max-workers', 
        type=int, 
        default=4,
        help='Maximum number of worker processes (default: 4)'
    )
    threshold_parser.set_defaults(func=run_threshold_optimization)


def run_threshold_optimization(args):
    """Execute threshold optimization analysis."""
    print("🔍 Running threshold optimization analysis...")
    batch_process(refresh_cache=args.refresh_cache, max_workers=args.max_workers)
    print("✅ Threshold analysis complete!")
