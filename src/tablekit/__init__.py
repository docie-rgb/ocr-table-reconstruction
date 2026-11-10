"""tablekit: rebuilds a table from OCR text boxes.

Input is a list of `ocrkit.TextItem` plus the source image (for ruling-line
detection and glyph geometry). It never calls the OCR engine itself.
"""
