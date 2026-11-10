"""End-to-end run: image -> OCR (ocrkit) -> table (tablekit) -> files in outputs/ocr/.

    python scripts/run_pipeline.py --config configs/census_table1.json
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import shutil
import sys
import time
from datetime import datetime, timezone
from importlib import metadata
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ocrkit import OCREngine, draw_boxes, draw_side_by_side  # noqa: E402
from ocrkit.visualize import crop  # noqa: E402
from tablekit.export import (write_cell_review_csv, write_document_md, write_review_log,  # noqa: E402
                             write_table_csv)
from tablekit.layout import build_layout, detect_rules  # noqa: E402
from tablekit.reconstruct import apply_manual_checks, reconstruct, run_sum_checks  # noqa: E402

PACKAGES = ["paddleocr", "paddlepaddle", "paddlex", "opencv-contrib-python", "numpy", "Pillow"]


def sha256(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def scrub(s: str) -> str:
    """Do not leak the local user name / home path into public files."""
    home = str(Path.home())
    return s.replace(home, "~").replace(home.replace("\\", "/"), "~")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="configs/census_table1.json")
    args = ap.parse_args()
    os.chdir(ROOT)
    cfg = json.loads(Path(args.config).read_text(encoding="utf-8"))

    out = Path(cfg["output_dir"])
    if out.exists():  # rebuild from scratch so no stale file survives a rerun
        shutil.rmtree(out)
    (out / "crops").mkdir(parents=True, exist_ok=True)
    src = Path(cfg["image"])
    if sha256(src) != cfg["source"]["sha256"]:
        print(f"[warn] {src} sha256 differs from config; input image is not the recorded original", file=sys.stderr)
    inp = out / f"input_{src.name}"
    shutil.copy2(src, inp)

    t0 = time.time()
    engine = OCREngine(**cfg["ocr"])
    t_load = time.time() - t0
    t0 = time.time()
    ocr = engine.run(inp)
    t_ocr = time.time() - t0
    ocr.image_path = inp.as_posix()
    ocr.raw["input_path"] = inp.as_posix()
    ocr.save_json(out / "raw_ocr.json")

    rules = detect_rules(inp, **cfg["table"].get("rule_detection", {}))
    layout = build_layout(ocr.items, rules, title_pattern=cfg["table"]["title_pattern"])
    low = cfg["table"]["low_score_threshold"]
    table = reconstruct(layout, inp, cfg["table"]["columns"], low_score=low)
    run_sum_checks(table, cfg.get("sum_checks", []))

    # Enlarged crop of every cell, used as evidence for the manual comparison.
    for row in table.rows:
        for k in table.column_keys:
            c = row[k]
            crop(inp, c.bbox, out / "crops" / f"r{c.row_no:02d}_{k}.png")

    manual_path = Path(cfg["manual_checks_file"])
    manual = json.loads(manual_path.read_text(encoding="utf-8")) if manual_path.exists() else {"checks": []}
    apply_manual_checks(table, manual)
    for m in table.manual_checks:
        if "row_no" in m:
            m["crop"] = f"crops/r{m['row_no']:02d}_{m['column']}.png"

    col_of = {it.id: layout.column_of(it) for it in ocr.items}
    draw_boxes(inp, ocr.items, out / "ocr_boxes.png", color_of=lambda it: col_of[it.id],
               lines={"horizontal": rules["horizontal"], "vertical": rules["vertical"]})
    draw_side_by_side(inp, ocr.items, out / "ocr_text_overlay.png")

    files = {"input": inp.name, "raw": "raw_ocr.json", "review_log": "review_log.md",
             "cell_review": "cell_review.csv"}
    write_table_csv(table, out / "table.csv")
    write_cell_review_csv(table, out / "cell_review.csv")
    write_document_md(table, out / "document.md", cfg["source"], files)
    write_review_log(table, out / "review_log.md", manual, low)
    (out / "corrections.json").write_text(json.dumps(
        {"changes": table.changes, "sum_checks": table.sum_checks, "manual_checks": table.manual_checks,
         "needs_review": table.review_items}, ensure_ascii=False, indent=2), encoding="utf-8")
    (out / "layout.json").write_text(json.dumps(
        {"ruling_lines": rules, "columns_x": layout.columns, "header_bottom_y": layout.header_bottom,
         "table_bottom_y": layout.table_bottom,
         "rows": [{"row_no": i + 1, "ocr_item_ids": [t.id for t in r.items], "y_center": round(r.yc, 1)}
                  for i, r in enumerate(layout.rows)],
         "header_item_ids": {table.column_keys[c]: [t.id for t in v] for c, v in layout.header_items.items()},
         "title_item_ids": [t.id for t in layout.title_items],
         "footnote_item_ids": [t.id for t in layout.footnote_items]}, indent=2), encoding="utf-8")

    settings = {k: v for k, v in ocr.engine_settings.items()}
    model_dir = Path.home() / ".paddlex" / "official_models"
    manifest = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "command": f"python scripts/run_pipeline.py --config {Path(args.config).as_posix()}",
        "source_image": {**cfg["source"], "repo_path": src.as_posix(), "copied_to": inp.as_posix(),
                         "sha256_actual": sha256(inp), "width": ocr.image_size[0], "height": ocr.image_size[1]},
        "ocr": {"engine": "PaddleOCR (local inference, no external OCR API)", "settings": settings,
                "models_cache_dir": scrub(str(model_dir)),
                "models_downloaded_from": "PaddleOCR official model hosters on first run (weights only)",
                "num_text_items": len(ocr.items),
                "timing_sec": {"model_load": round(t_load, 2), "inference": round(t_ocr, 2)}},
        "table": {"config": cfg["table"], "sum_checks": cfg.get("sum_checks", []),
                  "rows": len(table.rows), "columns": table.column_keys},
        "environment": {
            "python": sys.version.split()[0], "implementation": platform.python_implementation(),
            "os": platform.platform(), "machine": platform.machine(), "processor": platform.processor(),
            "cpu_count": os.cpu_count(), "device_used": settings.get("device"),
            "packages": {p: metadata.version(p) for p in PACKAGES},
        },
        "outputs": sorted(p.relative_to(out).as_posix() for p in out.rglob("*") if p.is_file()) + ["manifest.json"],
    }
    (out / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"OCR items: {len(ocr.items)}  rows: {len(table.rows)}  columns: {table.column_keys}")
    print("sum checks:", [(s['total'][:20], s['column'], s['result']) for s in table.sum_checks])
    print("manual checks:", [(m['row_label'], m['column'], m['result']) for m in table.manual_checks])
    print("needs review:", len(table.review_items))
    print(f"wrote {out}/")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
