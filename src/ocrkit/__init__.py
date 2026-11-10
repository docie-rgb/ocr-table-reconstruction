"""ocrkit: table-agnostic OCR layer.

This package only knows about images and text boxes (text, score, polygon,
bbox). It has no knowledge of tables, so it can be reused by other consumers
(e.g. a future comic speech-bubble pipeline) without change.
"""
from .engine import OCREngine, OCRResult, TextItem
from .visualize import draw_boxes, draw_side_by_side

__all__ = ["OCREngine", "OCRResult", "TextItem", "draw_boxes", "draw_side_by_side"]
