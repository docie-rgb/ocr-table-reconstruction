"""Text normalisation rules. Every change is returned so it can be logged."""
from __future__ import annotations

import re
import statistics
from pathlib import Path

from ocrkit.visualize import ink_components

NUMBER_RE = re.compile(r"^\d{1,3}(,\d{3})*$")
LEADER_RE = re.compile(r"[\s.·…:]+$")


def clean_label(text: str) -> tuple[str, str | None]:
    """Strip dot-leader remnants ("Alaska........" -> "Alaska")."""
    out = LEADER_RE.sub("", text).strip()
    return out, ("trailing dot-leader removed" if out != text else None)


def clean_number(text: str) -> tuple[str, str | None]:
    """Remove spaces the scan puts after thousands separators ("101, 115, 487")."""
    out = re.sub(r"\s+", "", text)
    return out, ("whitespace removed inside number" if out != text else None)


def is_number(text: str) -> bool:
    return bool(NUMBER_RE.match(text))


def to_int(text: str) -> int:
    return int(text.replace(",", ""))


def superscript_prefix(image_path: str | Path, bbox: list[int]) -> dict:
    """Is the left-most glyph in the box a raised, smaller digit (footnote marker)?

    Compares the first ink component with the other full-height glyphs: a
    superscript ends well above the shared baseline and is shorter.
    """
    comps = ink_components(image_path, bbox)
    if len(comps) < 3:
        return {"is_superscript": False, "reason": "too few glyphs"}
    max_h = max(c[3] for c in comps)
    digits = [c for c in comps[1:] if c[3] >= 0.6 * max_h]          # drop commas
    if not digits:
        return {"is_superscript": False, "reason": "no full-height glyphs"}
    baseline = statistics.median(c[1] + c[3] for c in digits)
    digit_h = statistics.median(c[3] for c in digits)
    first = comps[0]
    first_bottom = first[1] + first[3]
    raised = baseline - first_bottom
    sup = raised >= 0.25 * digit_h and first[3] <= 0.85 * digit_h
    return {
        "is_superscript": bool(sup),
        "first_glyph_bbox_in_box": list(first),
        "first_glyph_bottom": int(first_bottom),
        "baseline": float(baseline),
        "digit_height": float(digit_h),
        "raised_px": float(raised),
        "rule": "raised >= 0.25*digit_height and height <= 0.85*digit_height",
    }
