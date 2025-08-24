"""
Data extraction and configuration utilities.
"""

import logging


def configure_logging(debug: bool = False):
    """
    Configure the logging level and format for the script.

    Args:
        debug (bool): If True, set logging to DEBUG level; otherwise INFO.
    """
    level = logging.DEBUG if debug else logging.INFO
    logging.basicConfig(level=level, format='%(levelname)s: %(message)s')
