"""
Mock OCR functionality for testing without Tesseract installed.
"""

def mock_ocr_text() -> str:
    """Return sample OCR text in the expected flight grid format (7 columns × 9 lines = 63 lines + row headers)."""
    return """Mon
1/15
$299
$309
$319
$329
$339
$349
$359

Tue
1/16
$329
$339
$349
$359
$369
$379
$389

Wed
1/17
$359
$369
$379
$389
$399
$409
$419

Thu
1/18
$279
$289
$299
$309
$319
$329
$339

Fri
1/19
$319
$329
$339
$349
$359
$369
$379

Sat
1/20
$399
$409
$419
$429
$439
$449
$459

Sun
1/21
$349
$359
$369
$379
$389
$399
$409

Departure
6:00 AM
7:00 AM
8:00 AM
9:00 AM
10:00 AM
11:00 AM
12:00 PM"""
