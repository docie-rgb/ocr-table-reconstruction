"""Turn a TableLayout into reviewed cells.

Status codes (also explained in review_log.md):
  OK               OCR text used as-is (format valid, score >= threshold)
  NORMALIZED       only whitespace / dot-leader cleanup
  CORRECTED        OCR text changed (e.g. footnote superscript split off); evidence logged
  BLANK            no text detected inside the cell region
  NEEDS_REVIEW     could not be confirmed -> value is "확인 필요" or flagged
"""
from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from .layout import TableLayout
from .normalize import clean_label, clean_number, is_number, superscript_prefix, to_int

NEEDS_REVIEW_TEXT = "확인 필요"


@dataclass
class Cell:
    row_no: int
    column: str
    column_header: str
    ocr_item_ids: list[int]
    ocr_raw: str | None
    ocr_score: float | None
    bbox: list[int]
    value: str                       # final value written to CSV
    footnote: str | None = None
    status: str = "OK"
    notes: list[str] = field(default_factory=list)
    arith_check: str = "n/a"         # pass / fail / n/a
    manual_check: str = "not_checked"  # match / mismatch / not_checked


@dataclass
class Table:
    title: str
    headers: dict[str, str]
    column_keys: list[str]
    rows: list[dict[str, Cell]]
    footnotes: list[dict[str, Any]]
    changes: list[dict[str, Any]]
    sum_checks: list[dict[str, Any]]
    manual_checks: list[dict[str, Any]]
    review_items: list[dict[str, Any]]

    def label(self, row: dict[str, Cell]) -> str:
        return row[self.column_keys[0]].value

    def find_row(self, label: str) -> dict[str, Cell] | None:
        return next((r for r in self.rows if self.label(r) == label), None)


def _union(bboxes: list[list[int]]) -> list[int]:
    return [min(b[0] for b in bboxes), min(b[1] for b in bboxes),
            max(b[2] for b in bboxes), max(b[3] for b in bboxes)]


def reconstruct(layout: TableLayout, image_path: str | Path, columns_cfg: list[dict[str, Any]],
                low_score: float = 0.90) -> Table:
    keys = [c["key"] for c in columns_cfg]
    if len(keys) != len(layout.columns):
        raise ValueError(f"config has {len(keys)} columns but {len(layout.columns)} were detected "
                         f"from ruling lines: {layout.columns}")

    headers = {k: " ".join(i.text for i in layout.header_items[ci]) for ci, k in enumerate(keys)}
    title = " ".join(i.text for i in layout.title_items)

    # Footnotes below the table: "1 Population in 1903."
    footnotes = []
    for it in layout.footnote_items:
        m = re.match(r"^(\d+)\s+(.*)$", it.text)
        footnotes.append({"marker": m.group(1) if m else None, "text": m.group(2) if m else it.text,
                          "ocr_raw": it.text, "ocr_item_id": it.id, "bbox": it.bbox, "score": it.score})
    markers = [f["marker"] for f in footnotes if f["marker"]]

    changes: list[dict[str, Any]] = []
    review: list[dict[str, Any]] = []
    rows: list[dict[str, Cell]] = []

    for r in layout.rows:
        y0 = min(i.y_min for i in r.items); y1 = max(i.y_max for i in r.items)
        row_no = len(rows) + 1
        row: dict[str, Cell] = {}
        for ci, cfg in enumerate(columns_cfg):
            k = cfg["key"]
            toks = [i for i in r.items if layout.column_of(i) == ci]
            x0, x1 = layout.columns[ci]
            if not toks:
                row[k] = Cell(row_no, k, headers[k], [], None, None, [x0, y0, x1, y1], "", status="BLANK",
                              notes=["no OCR text inside this cell region"])
                continue
            raw = " ".join(t.text for t in toks)
            score = min(t.score for t in toks)
            bbox = _union([t.bbox for t in toks])
            cell = Cell(row_no, k, headers[k], [t.id for t in toks], raw, score, bbox, raw)

            if cfg["type"] == "label":
                val, why = clean_label(raw)
            else:
                val, why = clean_number(raw)
            if why:
                cell.status = "NORMALIZED"; cell.notes.append(why)
                changes.append({"row_no": row_no, "column": k, "kind": "normalization", "ocr_raw": raw,
                                "new_value": val, "reason": why, "bbox": bbox})
            cell.value = val

            if cfg["type"] == "int":
                # Footnote marker fused into the number (superscript "1" in front of "7,635,426").
                if val and val[0] in markers and len(toks) == 1:
                    geo = superscript_prefix(image_path, toks[0].bbox)
                    stripped = val[1:]
                    if geo["is_superscript"] and is_number(stripped):
                        cell.footnote = val[0]
                        cell.status = "CORRECTED"
                        cell.notes.append(f"leading '{val[0]}' is a raised superscript -> footnote {val[0]}")
                        changes.append({"row_no": row_no, "column": k, "kind": "correction",
                                        "ocr_raw": raw, "new_value": stripped, "footnote": val[0],
                                        "reason": ("Leading digit is a superscript footnote marker fused into "
                                                   "the number by OCR (glyph geometry below); the marker matches "
                                                   f"footnote '{val[0]}' printed under the table."),
                                        "evidence": {"glyph_geometry": geo}, "bbox": bbox})
                        val = stripped
                        cell.value = val
                if not is_number(val):
                    cell.status = "NEEDS_REVIEW"; cell.value = NEEDS_REVIEW_TEXT
                    cell.notes.append(f"not a valid number: {val!r}")
                    review.append({"row_no": row_no, "column": k, "ocr_raw": raw, "reason": "invalid number format",
                                   "bbox": bbox})
            if score < low_score and cell.status != "NEEDS_REVIEW":
                cell.notes.append(f"low OCR score {score:.3f} < {low_score}")
                review.append({"row_no": row_no, "column": k, "ocr_raw": raw, "value": cell.value,
                               "reason": f"low OCR score {score:.3f}", "bbox": bbox})
            row[k] = cell
        rows.append(row)

    return Table(title=title, headers=headers, column_keys=keys, rows=rows, footnotes=footnotes,
                 changes=changes, sum_checks=[], manual_checks=[], review_items=review)


def run_sum_checks(table: Table, checks: list[dict[str, Any]]) -> None:
    """total == sum(parts) for every numeric column. BLANK cells contribute nothing."""
    num_cols = table.column_keys[1:]
    for chk in checks:
        total = table.find_row(chk["total"])
        parts = [table.find_row(p) for p in chk["parts"]]
        missing = [p for p, r in zip(chk["parts"], parts) if r is None] + ([chk["total"]] if total is None else [])
        for col in num_cols:
            rec: dict[str, Any] = {"total": chk["total"], "parts": chk["parts"], "column": col}
            if missing:
                rec.update(result="row_not_found", missing=missing)
                table.sum_checks.append(rec); continue
            cells = [r[col] for r in parts]
            if total[col].status in ("BLANK", "NEEDS_REVIEW") or any(c.status == "NEEDS_REVIEW" for c in cells):
                rec.update(result="not_computable")
                table.sum_checks.append(rec); continue
            s = sum(to_int(c.value) for c in cells if c.status != "BLANK")
            t = to_int(total[col].value)
            ok = s == t
            rec.update(result="pass" if ok else "fail", expected_total=t, sum_of_parts=s, difference=t - s,
                       blank_parts=[table.label(r) for r, c in zip(parts, cells) if c.status == "BLANK"])
            table.sum_checks.append(rec)
            for c in [total[col], *cells]:
                if c.status == "BLANK":
                    continue
                # A cell that took part in any failing check stays failed.
                c.arith_check = "fail" if (not ok or c.arith_check == "fail") else "pass"
            if not ok:
                table.review_items.append({"column": col, "reason": f"sum check failed: {chk['total']} "
                                           f"({t}) != sum of parts ({s})"})


def apply_manual_checks(table: Table, manual: dict[str, Any]) -> None:
    for m in manual.get("checks", []):
        row = table.find_row(m["row_label"])
        rec = {**m}
        if row is None or m["column"] not in row:
            rec["result"] = "row_or_column_not_found"
            table.manual_checks.append(rec); continue
        cell = row[m["column"]]
        expected = m["read_value"].replace(",", "") if m["column"] != table.column_keys[0] else m["read_value"]
        actual = cell.value.replace(",", "") if m["column"] != table.column_keys[0] else cell.value
        fn_ok = (m.get("read_footnote") or None) == cell.footnote
        ok = expected == actual and fn_ok
        rec.update(result="match" if ok else "mismatch", csv_value=cell.value, csv_footnote=cell.footnote,
                   row_no=cell.row_no, bbox=cell.bbox, ocr_raw=cell.ocr_raw)
        cell.manual_check = "match" if ok else "mismatch"
        if not ok:
            table.review_items.append({"row_no": cell.row_no, "column": cell.column,
                                       "reason": f"manual check mismatch: read {m['read_value']!r}, csv {cell.value!r}"})
        table.manual_checks.append(rec)


def cell_records(table: Table) -> list[dict[str, Any]]:
    out = []
    for row in table.rows:
        for k in table.column_keys:
            d = asdict(row[k])
            d["row_label"] = table.label(row)
            d["notes"] = "; ".join(d["notes"])
            out.append(d)
    return out
