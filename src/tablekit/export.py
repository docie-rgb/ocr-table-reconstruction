"""CSV / Markdown writers."""
from __future__ import annotations

import csv
from collections import Counter
from pathlib import Path
from typing import Any

from .reconstruct import NEEDS_REVIEW_TEXT, Table, cell_records


def _fmt(v: str) -> str:
    if v and v.isdigit():
        return f"{int(v):,}"
    return v


def footnote_columns(table: Table) -> list[str]:
    return [k for k in table.column_keys[1:] if any(r[k].footnote for r in table.rows)]


def write_table_csv(table: Table, path: Path) -> None:
    fn_cols = footnote_columns(table)
    with path.open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["row_no", *table.column_keys, *[f"{k}_footnote" for k in fn_cols]])
        for row in table.rows:
            vals = [row[k].value if i == 0 or row[k].value == NEEDS_REVIEW_TEXT else row[k].value.replace(",", "")
                    for i, k in enumerate(table.column_keys)]
            w.writerow([row[table.column_keys[0]].row_no, *vals,
                        *[row[k].footnote or "" for k in fn_cols]])


def write_cell_review_csv(table: Table, path: Path) -> None:
    recs = cell_records(table)
    cols = ["row_no", "row_label", "column", "column_header", "value", "footnote", "status", "ocr_raw",
            "ocr_score", "bbox", "ocr_item_ids", "arith_check", "manual_check", "notes"]
    with path.open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        for r in recs:
            w.writerow(r)


def write_document_md(table: Table, path: Path, source: dict[str, Any], files: dict[str, str]) -> None:
    k0 = table.column_keys[0]
    lines = [f"# {table.title}: {table.headers[k0]} (OCR 재구성 문서)", ""]
    lines += ["> 과제 B 결과물. 원본 이미지를 로컬 PaddleOCR(CPU)로 인식한 뒤 표 구조를 복원했습니다.",
              f"> 원본 이미지: `{files['input']}`", ""]
    op = source.get("original_publication")
    if isinstance(op, dict):
        lines += ["**출처**", "",
                  f"- {op['publisher']}, {op['title']}, {op['published']}년 발행, "
                  f"PDF {op['pdf_page']}쪽 (인쇄 {op['printed_page']}쪽), Table 1",
                  f"- PDF: <{op['pdf_url']}>",
                  f"- 이미지 제공: {source.get('provided_by', '')}",
                  f"- 출처 근거: {op.get('citation_basis', '')}", ""]
    hdr = [table.headers[k] or k for k in table.column_keys]
    lines.append("| " + " | ".join(hdr) + " |")
    lines.append("|" + "|".join([":---"] + ["---:"] * (len(hdr) - 1)) + "|")
    for row in table.rows:
        cells = []
        for k in table.column_keys:
            c = row[k]
            if c.status == "BLANK":
                v = "—"
            elif c.value == NEEDS_REVIEW_TEXT:
                v = f"**{NEEDS_REVIEW_TEXT}**"
            else:
                v = _fmt(c.value) if k != k0 else c.value
                if c.footnote:
                    v = f"<sup>{c.footnote}</sup>{v}"
            cells.append(v)
        lines.append("| " + " | ".join(cells) + " |")
    lines += ["", "**각주 (원본 표 하단)**", ""]
    for fn in table.footnotes:
        lines.append(f"- <sup>{fn['marker']}</sup> {fn['text']}")
    lines += ["", "**표기 규칙**", "",
              "- `—` : 원본에서 해당 칸이 점선(dot leader)만 있고 값이 없는 칸입니다. 0이 아닙니다.",
              f"- `{NEEDS_REVIEW_TEXT}` : 원본에서 판독할 수 없어 값을 추측하지 않은 칸입니다.",
              "- 숫자의 쉼표는 원본 표기를 따랐고, `table.csv`에는 쉼표 없는 정수로 저장했습니다.",
              "- 행 이름의 철자(예: *Porto Rico*)는 원본 표기를 그대로 유지했습니다.", ""]

    st = Counter(row[k].status for row in table.rows for k in table.column_keys)
    passes = sum(1 for s in table.sum_checks if s["result"] == "pass")
    mm = Counter(m["result"] for m in table.manual_checks)
    lines += ["## 처리 결과 요약", "",
              f"- 행 {len(table.rows)}개 × 열 {len(table.column_keys)}개 = 셀 {sum(st.values())}개",
              "- 셀 상태: " + ", ".join(f"{k} {v}" for k, v in sorted(st.items())),
              f"- 합계 검증: {passes}/{len(table.sum_checks)} 통과",
              f"- 원본 직접 대조: {len(table.manual_checks)}개 셀 (일치 {mm.get('match', 0)}, "
              f"불일치 {mm.get('mismatch', 0)})",
              f"- 확인 필요 항목: {len(table.review_items)}개", "",
              f"세부 근거는 [`review_log.md`]({files['review_log']}), 셀 단위 기록은 "
              f"[`cell_review.csv`]({files['cell_review']}), 원시 OCR은 [`raw_ocr.json`]({files['raw']})를 참고하세요.", ""]
    path.write_text("\n".join(lines), encoding="utf-8")


def write_review_log(table: Table, path: Path, manual_meta: dict[str, Any], low_score: float) -> None:
    L = ["# 검토 기록 (Review log)", "",
         "이 파일은 `scripts/run_pipeline.py`가 실행할 때마다 다시 생성합니다. "
         "사람이 판독한 값은 `review/manual_checks.json`에만 입력하고, 이 파일에서 직접 수정하지 않습니다.", "",
         "## 상태 코드", "",
         "| 코드 | 의미 |", "|---|---|",
         "| OK | OCR 값을 그대로 사용 (형식 정상, 점수 ≥ 기준값) |",
         "| NORMALIZED | 공백·점선 리더 제거 같은 표기 정리만 함 (내용은 그대로) |",
         "| CORRECTED | OCR 값을 수정함. 근거는 아래 '수정 내역'에 기록 |",
         "| BLANK | 셀 영역에서 글자가 검출되지 않음 (원본 공란 여부는 직접 대조로 확인) |",
         f"| NEEDS_REVIEW | 확인 필요. 값은 `{NEEDS_REVIEW_TEXT}`로 두거나 표시해 둠 |", "",
         f"저신뢰 기준: OCR 점수 < {low_score}", ""]

    L += ["## 1. 수정 내역 (OCR 원래값 → 수정값)", ""]
    corr = [c for c in table.changes if c["kind"] == "correction"]
    if corr:
        L += ["| 행 | 열 | OCR 원래값 | 수정값 | 각주 | 근거 | 위치 bbox (x0,y0,x1,y1) |", "|---|---|---|---|---|---|---|"]
        for c in corr:
            g = c["evidence"]["glyph_geometry"]
            ev = (f"{c['reason']} 첫 글자 하단 y={g['first_glyph_bottom']}, 숫자 기준선 y={g['baseline']:.0f}, "
                  f"{g['raised_px']:.0f}px 위로 떠 있고 높이 {g['first_glyph_bbox_in_box'][3]}px < 숫자 높이 "
                  f"{g['digit_height']:.0f}px. 수정 후 합계 검증은 아래 2절 참조.")
            label = table.label(table.rows[c["row_no"] - 1])
            L.append(f"| {c['row_no']} {label} | {c['column']} | `{c['ocr_raw']}` | `{c['new_value']}` | "
                     f"{c['footnote']} | {ev} | {c['bbox']} |")
    else:
        L.append("수정한 값이 없습니다.")
    L += ["", "### 표기 정리 (내용 변경 없음)", "", "| 행 | 열 | OCR 원래값 | 정리 후 | 규칙 |", "|---|---|---|---|---|"]
    for c in table.changes:
        if c["kind"] == "normalization":
            L.append(f"| {c['row_no']} | {c['column']} | `{c['ocr_raw']}` | `{c['new_value']}` | {c['reason']} |")

    L += ["", "## 2. 합계 검증 (표 내부 산술 대조)", "",
          "원본 표의 상위 행이 하위 행들의 합인지 확인했습니다. 숫자 하나하나의 정답을 증명하지는 않지만, "
          "한 자리라도 잘못 읽히면 대부분 합계가 깨집니다.", "",
          "| 합계 행 | 열 | 합계 값 | 부분 합 | 차이 | 결과 | 공란으로 제외된 행 |", "|---|---|---:|---:|---:|---|---|"]
    for s in table.sum_checks:
        L.append(f"| {s['total']} | {s['column']} | {s.get('expected_total', '')} | {s.get('sum_of_parts', '')} | "
                 f"{s.get('difference', '')} | {s['result']} | {', '.join(s.get('blank_parts', [])) or '-'} |")

    L += ["", "## 3. 원본 이미지 직접 대조", "",
          f"- 검토자: {manual_meta.get('reviewer', '(미기재)')}",
          f"- 방법: {manual_meta.get('method', '(미기재)')}",
          f"- 판독일: {manual_meta.get('date', '(미기재)')}", "",
          "| 행 | 열 | 원본 위치 bbox | 확대 이미지 | 원본 판독값 | CSV 값 | 결과 | 메모 |", "|---|---|---|---|---|---|---|---|"]
    for m in table.manual_checks:
        crop = m.get("crop", "")
        L.append(f"| {m.get('row_no', '')} {m['row_label']} | {m['column']} | {m.get('bbox', '')} | "
                 f"[{Path(crop).name}]({crop}) | `{m['read_value']}`{' (각주 ' + m['read_footnote'] + ')' if m.get('read_footnote') else ''} | "
                 f"`{m.get('csv_value', '')}` | {m['result']} | {m.get('note', '')} |")
    checked = {(m.get("row_no"), m["column"]) for m in table.manual_checks}
    unchecked = [(r[table.column_keys[0]].row_no, k) for r in table.rows for k in table.column_keys
                 if (r[table.column_keys[0]].row_no, k) not in checked]
    L += ["", f"직접 대조하지 않은 셀: {len(unchecked)}개. 이 셀들은 '확인 완료'로 표시하지 않았으며 "
          "`cell_review.csv`의 `manual_check` 값이 `not_checked`입니다. 이 중 숫자 셀은 2절 합계 검증으로, "
          "행 이름 셀은 OCR 점수로만 뒷받침됩니다.", "",
          "목록: " + ", ".join(f"{r}행 {k}" for r, k in unchecked), "",
          "표 머리글(헤더)과 표 아래 각주 문장은 셀 대조 대상에 포함하지 않았습니다 "
          "(OCR 원문은 `raw_ocr.json`, 위치는 `ocr_boxes.png`에서 확인 가능).", ""]

    hr = manual_meta.get("human_review")
    if hr:
        L += ["## 3-1. 사람 검토 요청", "",
              f"- 상태: **{hr.get('status', 'pending')}**. 사람 검토자가 확인하기 전까지 아래 셀은 사람이 검증한 것으로 보지 않습니다.",
              f"- 검토자: {hr.get('reviewer') or '(미확인)'} · 확인일: {hr.get('date') or '(미확인)'}", "",
              "| 확대 이미지 | 행 | 열 | CSV 값 | 확인할 사항 | 사람 판독값 | 결과 |", "|---|---|---|---|---|---|---|"]
        for c in hr.get("cells", []):
            row = table.find_row(c["row_label"])
            cell = row[c["column"]] if row else None
            csv_v = "" if cell is None else (cell.value.replace(",", "") if c["column"] != table.column_keys[0] else cell.value)
            if cell is not None and cell.status == "BLANK":
                csv_v = "(빈 칸)"
            if cell is not None and cell.footnote:
                csv_v += f" (각주 {cell.footnote})"
            fn = f"crops/r{cell.row_no:02d}_{c['column']}.png" if cell else ""
            read = c.get("human_read_value")
            L.append(f"| [{Path(fn).name}]({fn}) | {cell.row_no if cell else ''} {c['row_label']} | {c['column']} | "
                     f"`{csv_v}` | {c['what_to_check']} | {'`' + read + '`' if read is not None else '(미확인)'} | "
                     f"{c.get('human_result') or '미확인'} |")
        L.append("")

    L += ["## 4. 확인 필요 항목", ""]
    if table.review_items:
        L += ["| 행 | 열 | 사유 | OCR 원래값 | bbox |", "|---|---|---|---|---|"]
        for r in table.review_items:
            L.append(f"| {r.get('row_no', '')} | {r.get('column', '')} | {r['reason']} | `{r.get('ocr_raw', '')}` | {r.get('bbox', '')} |")
    else:
        L.append("자동 규칙(형식 검사, 저신뢰 점수, 합계 검증, 직접 대조 불일치)에 걸린 항목은 없습니다. "
                 "다만 3절에서 직접 대조하지 않은 셀은 '미확인' 상태입니다.")
    L.append("")
    path.write_text("\n".join(L), encoding="utf-8")
