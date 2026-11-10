"""Checks that a pipeline run produced every required file and a consistent table.

    python scripts/verify_outputs.py
Exit code 0 = all checks passed.
"""
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs" / "ocr"
REQUIRED = ["input_census_table1.png", "raw_ocr.json", "ocr_boxes.png", "ocr_text_overlay.png", "table.csv",
            "document.md", "manifest.json", "review_log.md", "cell_review.csv", "corrections.json", "layout.json"]
# Shape of the original Table 1: 11 data rows, label + 2 numeric columns (+ footnote column).
EXPECTED_HEADER = ["row_no", "area", "gross_area_sq_mi", "population_1910", "population_1910_footnote"]
EXPECTED_ROWS = 11

failures: list[str] = []


def check(cond: bool, msg: str) -> None:
    print(("PASS " if cond else "FAIL ") + msg)
    if not cond:
        failures.append(msg)


for f in REQUIRED:
    p = OUT / f
    check(p.exists() and p.stat().st_size > 0, f"exists: outputs/ocr/{f}")

if (OUT / "table.csv").exists():
    rows = list(csv.reader((OUT / "table.csv").open(encoding="utf-8-sig")))
    check(rows[0] == EXPECTED_HEADER, f"table.csv header == {EXPECTED_HEADER}")
    check(len(rows) - 1 == EXPECTED_ROWS, f"table.csv has {EXPECTED_ROWS} data rows (got {len(rows) - 1})")
    check(all(len(r) == len(EXPECTED_HEADER) for r in rows), "every CSV row has the same number of columns")

if (OUT / "corrections.json").exists():
    c = json.loads((OUT / "corrections.json").read_text(encoding="utf-8"))
    check(all(s["result"] == "pass" for s in c["sum_checks"]) and c["sum_checks"],
          f"all {len(c['sum_checks'])} sum checks pass")
    check(all(m["result"] == "match" for m in c["manual_checks"]),
          f"all {len(c['manual_checks'])} manual checks match")

if (OUT / "manifest.json").exists():
    m = json.loads((OUT / "manifest.json").read_text(encoding="utf-8"))
    check(m["source_image"]["sha256"] == m["source_image"]["sha256_actual"], "input image sha256 matches config")
    check(m["environment"]["device_used"] == "cpu", "ran on CPU")

print("\nRESULT:", "OK" if not failures else f"{len(failures)} failure(s)")
sys.exit(1 if failures else 0)
