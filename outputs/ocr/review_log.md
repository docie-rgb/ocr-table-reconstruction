# 검토 기록 (Review log)

이 파일은 `scripts/run_pipeline.py`가 실행할 때마다 다시 생성합니다. 사람이 판독한 값은 `review/manual_checks.json`에만 입력하고, 이 파일에서 직접 수정하지 않습니다.

## 상태 코드

| 코드 | 의미 |
|---|---|
| OK | OCR 값을 그대로 사용 (형식 정상, 점수 ≥ 기준값) |
| NORMALIZED | 공백·점선 리더 제거 같은 표기 정리만 함 (내용은 그대로) |
| CORRECTED | OCR 값을 수정함. 근거는 아래 '수정 내역'에 기록 |
| BLANK | 셀 영역에서 글자가 검출되지 않음 (원본 공란 여부는 직접 대조로 확인) |
| NEEDS_REVIEW | 확인 필요. 값은 `확인 필요`로 두거나 표시해 둠 |

저신뢰 기준: OCR 점수 < 0.9

## 1. 수정 내역 (OCR 원래값 → 수정값)

| 행 | 열 | OCR 원래값 | 수정값 | 각주 | 근거 | 위치 bbox (x0,y0,x1,y1) |
|---|---|---|---|---|---|---|
| 8 Philippine Islands | population_1910 | `17,635,426` | `7,635,426` | 1 | Leading digit is a superscript footnote marker fused into the number by OCR (glyph geometry below); the marker matches footnote '1' printed under the table. 첫 글자 하단 y=15, 숫자 기준선 y=22, 7px 위로 떠 있고 높이 10px < 숫자 높이 17px. 수정 후 합계 검증은 아래 2절 참조. | [921, 340, 1035, 365] |
| 9 Panama Canal Zone | population_1910 | `262,810` | `62,810` | 2 | Leading digit is a superscript footnote marker fused into the number by OCR (glyph geometry below); the marker matches footnote '2' printed under the table. 첫 글자 하단 y=15, 숫자 기준선 y=21, 6px 위로 떠 있고 높이 11px < 숫자 높이 16px. 수정 후 합계 검증은 아래 2절 참조. | [952, 363, 1035, 388] |

### 표기 정리 (내용 변경 없음)

| 행 | 열 | OCR 원래값 | 정리 후 | 규칙 |
|---|---|---|---|---|
| 1 | population_1910 | `101, 115, 487` | `101,115,487` | whitespace removed inside number |
| 2 | area | `United States, exclusive of outlying possessions.` | `United States, exclusive of outlying possessions` | trailing dot-leader removed |
| 2 | population_1910 | `91, 972,266` | `91,972,266` | whitespace removed inside number |
| 3 | area | `Outlying possessions.` | `Outlying possessions` | trailing dot-leader removed |
| 4 | area | `Alaska.` | `Alaska` | trailing dot-leader removed |
| 5 | area | `Hawaii.` | `Hawaii` | trailing dot-leader removed |
| 6 | area | `Porto Rico.` | `Porto Rico` | trailing dot-leader removed |
| 8 | area | `Philippine Islands.` | `Philippine Islands` | trailing dot-leader removed |

## 2. 합계 검증 (표 내부 산술 대조)

원본 표의 상위 행이 하위 행들의 합인지 확인했습니다. 숫자 하나하나의 정답을 증명하지는 않지만, 한 자리라도 잘못 읽히면 대부분 합계가 깨집니다.

| 합계 행 | 열 | 합계 값 | 부분 합 | 차이 | 결과 | 공란으로 제외된 행 |
|---|---|---:|---:|---:|---|---|
| United States, with outlying possessions | gross_area_sq_mi | 3743306 | 3743306 | 0 | pass | - |
| United States, with outlying possessions | population_1910 | 101115487 | 101115487 | 0 | pass | - |
| Outlying possessions | gross_area_sq_mi | 716517 | 716517 | 0 | pass | Military and naval service abroad |
| Outlying possessions | population_1910 | 9143221 | 9143221 | 0 | pass | - |

## 3. 원본 이미지 직접 대조

- 검토자: Claude (AI 코딩 보조, 과제 수행자 요청으로 판독). 사람 검토자가 아니므로 제출 전 과제 수행자가 동일 확대 이미지로 재확인할 것을 권장
- 방법: 파이프라인이 원본 이미지 좌표(bbox)로 잘라 3배 확대한 셀 이미지(outputs/ocr/crops/)와 원본 전체 이미지를 눈으로 읽고, 읽은 값을 이 파일에 입력. 파이프라인이 CSV 값과 자동 비교함. OCR 결과를 보고 옮겨 적지 않고 이미지 글자를 기준으로 판독함
- 판독일: 2026-11-10

| 행 | 열 | 원본 위치 bbox | 확대 이미지 | 원본 판독값 | CSV 값 | 결과 | 메모 |
|---|---|---|---|---|---|---|---|
| 1 United States, with outlying possessions | area | [93, 119, 515, 142] | [r01_area.png](crops/r01_area.png) | `United States, with outlying possessions` | `United States, with outlying possessions` | match | 굵은 글씨 합계 행, 뒤는 점선 |
| 1 United States, with outlying possessions | gross_area_sq_mi | [727, 118, 833, 142] | [r01_gross_area_sq_mi.png](crops/r01_gross_area_sq_mi.png) | `3,743,306` | `3,743,306` | match | 굵은 글씨. 첫 자리 3 |
| 1 United States, with outlying possessions | population_1910 | [909, 118, 1033, 144] | [r01_population_1910.png](crops/r01_population_1910.png) | `101,115,487` | `101,115,487` | match | 원본은 쉼표 뒤 공백 있음 |
| 3 Outlying possessions | population_1910 | [929, 204, 1035, 235] | [r03_population_1910.png](crops/r03_population_1910.png) | `9,143,221` | `9,143,221` | match |  |
| 4 Alaska | area | [69, 251, 149, 275] | [r04_area.png](crops/r04_area.png) | `Alaska` | `Alaska` | match | 뒤 점선 리더 제거 |
| 4 Alaska | gross_area_sq_mi | [749, 249, 835, 276] | [r04_gross_area_sq_mi.png](crops/r04_gross_area_sq_mi.png) | `590,884` | `590,884` | match |  |
| 4 Alaska | population_1910 | [963, 251, 1036, 276] | [r04_population_1910.png](crops/r04_population_1910.png) | `64,356` | `64,356` | match |  |
| 5 Hawaii | gross_area_sq_mi | [769, 271, 835, 300] | [r05_gross_area_sq_mi.png](crops/r05_gross_area_sq_mi.png) | `6,449` | `6,449` | match |  |
| 6 Porto Rico | population_1910 | [930, 297, 1035, 321] | [r06_population_1910.png](crops/r06_population_1910.png) | `1,118,012` | `1,118,012` | match | 행 이름은 원본 철자 Porto Rico |
| 7 Military and naval service abroad | area | [69, 319, 424, 342] | [r07_area.png](crops/r07_area.png) | `Military and naval service abroad` | `Military and naval service abroad` | match |  |
| 7 Military and naval service abroad | gross_area_sq_mi | [670, 319, 856, 343] | [r07_gross_area_sq_mi.png](crops/r07_gross_area_sq_mi.png) | `` | `` | match | 원본 칸에 점선만 있고 숫자 없음. 공란으로 유지(0으로 채우지 않음) |
| 8 Philippine Islands | gross_area_sq_mi | [748, 338, 834, 366] | [r08_gross_area_sq_mi.png](crops/r08_gross_area_sq_mi.png) | `115,026` | `115,026` | match |  |
| 8 Philippine Islands | population_1910 | [921, 340, 1035, 365] | [r08_population_1910.png](crops/r08_population_1910.png) | `7,635,426` (각주 1) | `7,635,426` | match | 숫자 앞 작은 위첨자 1 = 각주 'Population in 1903.' |
| 9 Panama Canal Zone | gross_area_sq_mi | [793, 362, 834, 386] | [r09_gross_area_sq_mi.png](crops/r09_gross_area_sq_mi.png) | `436` | `436` | match |  |
| 9 Panama Canal Zone | population_1910 | [952, 363, 1035, 388] | [r09_population_1910.png](crops/r09_population_1910.png) | `62,810` (각주 2) | `62,810` | match | 숫자 앞 작은 위첨자 2 = 각주 'Population in 1912.' |
| 11 Samoa (population estimated) | area | [69, 408, 383, 432] | [r11_area.png](crops/r11_area.png) | `Samoa (population estimated)` | `Samoa (population estimated)` | match |  |
| 11 Samoa (population estimated) | gross_area_sq_mi | [802, 406, 834, 431] | [r11_gross_area_sq_mi.png](crops/r11_gross_area_sq_mi.png) | `77` | `77` | match |  |
| 11 Samoa (population estimated) | population_1910 | [971, 406, 1036, 435] | [r11_population_1910.png](crops/r11_population_1910.png) | `6,100` | `6,100` | match |  |

직접 대조하지 않은 셀: 15개. 이 셀들은 '확인 완료'로 표시하지 않았으며 `cell_review.csv`의 `manual_check` 값이 `not_checked`입니다. 이 중 숫자 셀은 2절 합계 검증으로, 행 이름 셀은 OCR 점수로만 뒷받침됩니다.

목록: 2행 area, 2행 gross_area_sq_mi, 2행 population_1910, 3행 area, 3행 gross_area_sq_mi, 5행 area, 5행 population_1910, 6행 area, 6행 gross_area_sq_mi, 7행 population_1910, 8행 area, 9행 area, 10행 area, 10행 gross_area_sq_mi, 10행 population_1910

표 머리글(헤더)과 표 아래 각주 문장은 셀 대조 대상에 포함하지 않았습니다 (OCR 원문은 `raw_ocr.json`, 위치는 `ocr_boxes.png`에서 확인 가능).

## 3-1. 사람 검토 요청

- 상태: **pending**. 사람 검토자가 확인하기 전까지 아래 셀은 사람이 검증한 것으로 보지 않습니다.
- 검토자: (미확인) · 확인일: (미확인)

| 확대 이미지 | 행 | 열 | CSV 값 | 확인할 사항 | 사람 판독값 | 결과 |
|---|---|---|---|---|---|---|
| [r08_population_1910.png](crops/r08_population_1910.png) | 8 Philippine Islands | population_1910 | `7635426 (각주 1)` | 숫자 앞 '1'이 본문 숫자보다 작고 위로 올라간 위첨자인지, 그 뒤 숫자가 7,635,426인지 | (미확인) | 미확인 |
| [r09_population_1910.png](crops/r09_population_1910.png) | 9 Panama Canal Zone | population_1910 | `62810 (각주 2)` | 숫자 앞 '2'가 위첨자인지, 그 뒤 숫자가 62,810인지 | (미확인) | 미확인 |
| [r01_gross_area_sq_mi.png](crops/r01_gross_area_sq_mi.png) | 1 United States, with outlying possessions | gross_area_sq_mi | `3743306` | 3,743,306인지 (첫 자리 3) | (미확인) | 미확인 |
| [r02_population_1910.png](crops/r02_population_1910.png) | 2 United States, exclusive of outlying possessions | population_1910 | `91972266` | 91,972,266인지 | (미확인) | 미확인 |
| [r07_gross_area_sq_mi.png](crops/r07_gross_area_sq_mi.png) | 7 Military and naval service abroad | gross_area_sq_mi | `(빈 칸)` | 칸에 숫자 없이 점선만 있는지 | (미확인) | 미확인 |
| [r10_gross_area_sq_mi.png](crops/r10_gross_area_sq_mi.png) | 10 Guam (population estimated) | gross_area_sq_mi | `210` | 210인지, 앞의 2가 일반 크기 숫자인지 | (미확인) | 미확인 |

## 4. 확인 필요 항목

자동 규칙(형식 검사, 저신뢰 점수, 합계 검증, 직접 대조 불일치)에 걸린 항목은 없습니다. 다만 3절에서 직접 대조하지 않은 셀은 '미확인' 상태입니다.
