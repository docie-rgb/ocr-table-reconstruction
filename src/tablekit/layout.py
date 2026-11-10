"""Row / column structure from ruling lines + text-box coordinates."""
from __future__ import annotations

import re
import statistics
from dataclasses import dataclass, field
from pathlib import Path

import cv2
import numpy as np

from ocrkit.engine import TextItem


def _group(positions: list[int], merge_px: int) -> list[int]:
    out: list[list[int]] = []
    for p in sorted(positions):
        if out and p - out[-1][-1] <= merge_px:
            out[-1].append(p)
        else:
            out.append([p])
    return [int(round(sum(g) / len(g))) for g in out]


def detect_rules(image_path: str | Path, min_frac: float = 0.25, merge_px: int = 8,
                 border_px: int = 12) -> dict[str, list[int]]:
    """Horizontal / vertical ruling lines via morphological opening.

    Scanned lines are broken, so a line only has to be >= min_frac of the image
    size. Lines within `border_px` of the image edge are reported but tagged as
    border lines (they do not split columns).
    """
    g = cv2.imread(str(image_path), cv2.IMREAD_GRAYSCALE)
    b = cv2.threshold(g, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)[1]
    h, w = b.shape
    hl = cv2.morphologyEx(b, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_RECT, (int(w * min_frac), 1)))
    vl = cv2.morphologyEx(b, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_RECT, (1, int(h * min_frac))))
    ys = _group(np.where(hl.sum(1) > 0)[0].tolist(), merge_px)
    xs = _group(np.where(vl.sum(0) > 0)[0].tolist(), merge_px)
    return {
        "horizontal": ys,
        "vertical": [x for x in xs if border_px < x < w - border_px],
        "vertical_border": [x for x in xs if not (border_px < x < w - border_px)],
        "image_size": [w, h],
    }


@dataclass
class Row:
    index: int
    items: list[TextItem] = field(default_factory=list)

    @property
    def yc(self) -> float:
        return statistics.mean(i.yc for i in self.items)


@dataclass
class TableLayout:
    columns: list[tuple[int, int]]              # x ranges, column 0 = row labels
    header_bottom: int
    table_bottom: int
    title_items: list[TextItem]
    header_items: dict[int, list[TextItem]]     # column -> tokens
    rows: list[Row]
    footnote_items: list[TextItem]
    unassigned: list[TextItem]

    def column_of(self, it: TextItem) -> int:
        for ci, (x0, x1) in enumerate(self.columns):
            if x0 <= it.xc < x1:
                return ci
        return len(self.columns) - 1


def build_layout(items: list[TextItem], rules: dict[str, list[int]], title_pattern: str = r"^Table\s+\d+",
                 row_tol_ratio: float = 0.5) -> TableLayout:
    w, _ = rules["image_size"]
    bounds = [0, *rules["vertical"], w + 1]
    columns = [(bounds[i], bounds[i + 1]) for i in range(len(bounds) - 1)]

    # Header bottom: first horizontal rule with text both above and below it.
    # Table bottom: last horizontal rule with text above it (footnotes sit below).
    hs = rules["horizontal"]
    header_bottom = next(y for y in hs if any(i.yc < y for i in items) and any(i.yc > y for i in items))
    table_bottom = max(y for y in hs if any(i.yc < y for i in items))

    layout = TableLayout(columns=columns, header_bottom=header_bottom, table_bottom=table_bottom,
                         title_items=[], header_items={c: [] for c in range(len(columns))},
                         rows=[], footnote_items=[], unassigned=[])

    body: list[TextItem] = []
    for it in items:
        if it.yc < header_bottom:
            if layout.column_of(it) == 0 and re.match(title_pattern, it.text):
                layout.title_items.append(it)
            else:
                layout.header_items[layout.column_of(it)].append(it)
        elif it.yc > table_bottom:
            layout.footnote_items.append(it)
        else:
            body.append(it)

    # Row clustering by vertical centre.
    if body:
        tol = statistics.median(i.height for i in body) * row_tol_ratio
        for it in sorted(body, key=lambda i: i.yc):
            if layout.rows and abs(it.yc - layout.rows[-1].yc) <= tol:
                layout.rows[-1].items.append(it)
            else:
                layout.rows.append(Row(index=len(layout.rows), items=[it]))
    for r in layout.rows:
        r.items.sort(key=lambda i: i.x_min)
    for c in layout.header_items:
        layout.header_items[c].sort(key=lambda i: (i.y_min, i.x_min))
    layout.footnote_items.sort(key=lambda i: i.x_min)
    return layout
