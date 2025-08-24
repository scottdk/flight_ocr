"""
Mock OCR functionality for testing without Tesseract installed.
Provides a function that returns sample OCR text in the expected flight grid format 
(7 columns × 9 lines = 63 lines + row headers).
"""


def mock_ocr_text() -> str:
    """Return sample OCR text in the expected flight grid format (7 columns × 9 lines = 63 lines + row headers)."""
    return """Sun
Aug24
$299
$309
$319
$329
$339
$349
$359
Mon
Aug25
$299
$309
$319
$329
$339
$349
$359
Tue
Aug26
$299
$309
$319
$329
$339
$349
$359
Wed
Aug27
$359
$369
$379
$389
$399
$409
$419
Thu
Aug28
$279
$289
$299
$309
$319
$329
$339
Fri
Aug29
$319
$329
$339
$349
$359
$369
$379
Sat
Aug30
$399
$409
$419
$429
$439
$449
$459
Sun
Aug31
Mon
Sep1
Tue
Sep2
Wed
Sep3
Thu
Sep4
Fri
Sep5
Sat
Sep6"""
