"""Draw OCR boxes / recognised text on top of the source image."""
from __future__ import annotations

from pathlib import Path
from typing import Callable, Iterable

import numpy as np
from PIL import Image, ImageDraw, ImageFont

from .engine import TextItem

PALETTE = [(220, 38, 38), (37, 99, 235), (22, 163, 74), (217, 119, 6), (147, 51, 234), (8, 145, 178)]


def _font(size: int) -> ImageFont.ImageFont:
    for name in ("arial.ttf", "DejaVuSans.ttf", "LiberationSans-Regular.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default(size=size)


def draw_boxes(image_path: str | Path, items: Iterable[TextItem], out_path: str | Path,
               color_of: Callable[[TextItem], int] | None = None,
               lines: dict[str, list[int]] | None = None) -> None:
    """Original image + polygon per text box + box id. Optionally draws detected ruling lines."""
    img = Image.open(image_path).convert("RGB")
    d = ImageDraw.Draw(img)
    f = _font(11)
    if lines:
        for y in lines.get("horizontal", []):
            d.line([(0, y), (img.width, y)], fill=(250, 204, 21), width=1)
        for x in lines.get("vertical", []):
            d.line([(x, 0), (x, img.height)], fill=(250, 204, 21), width=1)
    for it in items:
        c = PALETTE[(color_of(it) if color_of else 0) % len(PALETTE)]
        d.polygon([tuple(p) for p in it.poly], outline=c, width=2)
        d.text((it.x_min, max(0, it.y_min - 12)), f"#{it.id}", fill=c, font=f)
    img.save(out_path)


def draw_side_by_side(image_path: str | Path, items: Iterable[TextItem], out_path: str | Path) -> None:
    """Left: original with boxes. Right: recognised text re-drawn at the same coordinates."""
    items = list(items)
    src = Image.open(image_path).convert("RGB")
    left = src.copy()
    dl = ImageDraw.Draw(left)
    right = Image.new("RGB", src.size, "white")
    dr = ImageDraw.Draw(right)
    for it in items:
        c = PALETTE[it.id % len(PALETTE)]
        dl.polygon([tuple(p) for p in it.poly], outline=c, width=2)
        dr.rectangle(it.bbox, outline=c, width=1)
        size = max(9, int(it.height * 0.6))
        dr.text((it.x_min + 2, it.y_min + 1), it.text, fill=(0, 0, 0), font=_font(size))
        dr.text((it.x_min, max(0, it.y_min - 11)), f"#{it.id} {it.score:.3f}", fill=c, font=_font(9))
    canvas = Image.new("RGB", (src.width * 2 + 10, src.height), (200, 200, 200))
    canvas.paste(left, (0, 0))
    canvas.paste(right, (src.width + 10, 0))
    canvas.save(out_path)


def crop(image_path: str | Path, bbox: list[int], out_path: str | Path, pad: int = 6, scale: int = 3) -> None:
    """Enlarged crop of one region, used as evidence for manual comparison."""
    img = Image.open(image_path).convert("RGB")
    x0, y0, x1, y1 = bbox
    box = (max(0, x0 - pad), max(0, y0 - pad), min(img.width, x1 + pad), min(img.height, y1 + pad))
    c = img.crop(box)
    c = c.resize((c.width * scale, c.height * scale), Image.NEAREST)
    c.save(out_path)


def ink_components(image_path: str | Path, bbox: list[int]) -> list[tuple[int, int, int, int]]:
    """Connected components (x, y, w, h) of dark pixels inside bbox, in bbox coordinates."""
    import cv2
    g = cv2.imread(str(image_path), cv2.IMREAD_GRAYSCALE)
    x0, y0, x1, y1 = bbox
    roi = g[y0:y1, x0:x1]
    b = cv2.threshold(roi, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)[1]
    n, _, stats, _ = cv2.connectedComponentsWithStats(b, 8)
    comps = [tuple(int(v) for v in stats[i][:4]) for i in range(1, n) if stats[i][4] >= 3]
    return sorted(comps, key=lambda c: c[0])


__all__ = ["draw_boxes", "draw_side_by_side", "crop", "ink_components"]
