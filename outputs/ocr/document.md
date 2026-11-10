# Table 1: AREA. (OCR 재구성 문서)

> 과제 B 결과물. 원본 이미지를 로컬 PaddleOCR(CPU)로 인식한 뒤 표 구조를 복원했습니다.
> 원본 이미지: `input_census_table1.png`

**출처**

- U.S. Bureau of the Census (미국 인구조사국), 1910 인구조사 보고서 (PDF 경로상 Volume 1), 1913년 발행, PDF 2쪽 (인쇄 22쪽), Table 1
- PDF: <https://www2.census.gov/library/publications/decennial/1910/volume-1/volume-1-p3.pdf>
- 이미지 제공: AI 교육 과정 선택 과제 B 자료
- 출처 근거: 과제 안내문에 기재된 출처 정보. 이 PDF를 직접 내려받아 이미지와 대조하지는 않음

| AREA. | Gross area (land and water) in square miles. | Population: 1910 |
|:---|---:|---:|
| United States, with outlying possessions | 3,743,306 | 101,115,487 |
| United States, exclusive of outlying possessions | 3,026,789 | 91,972,266 |
| Outlying possessions | 716,517 | 9,143,221 |
| Alaska | 590,884 | 64,356 |
| Hawaii | 6,449 | 191,909 |
| Porto Rico | 3,435 | 1,118,012 |
| Military and naval service abroad | — | 55,608 |
| Philippine Islands | 115,026 | <sup>1</sup>7,635,426 |
| Panama Canal Zone | 436 | <sup>2</sup>62,810 |
| Guam (population estimated) | 210 | 9,000 |
| Samoa (population estimated) | 77 | 6,100 |

**각주 (원본 표 하단)**

- <sup>1</sup> Population in 1903.
- <sup>2</sup> Population in 1912.

**표기 규칙**

- `—` : 원본에서 해당 칸이 점선(dot leader)만 있고 값이 없는 칸입니다. 0이 아닙니다.
- `확인 필요` : 원본에서 판독할 수 없어 값을 추측하지 않은 칸입니다.
- 숫자의 쉼표는 원본 표기를 따랐고, `table.csv`에는 쉼표 없는 정수로 저장했습니다.
- 행 이름의 철자(예: *Porto Rico*)는 원본 표기를 그대로 유지했습니다.

## 처리 결과 요약

- 행 11개 × 열 3개 = 셀 33개
- 셀 상태: BLANK 1, CORRECTED 2, NORMALIZED 8, OK 22
- 합계 검증: 4/4 통과
- 원본 직접 대조: 18개 셀 (일치 18, 불일치 0)
- 확인 필요 항목: 0개

세부 근거는 [`review_log.md`](review_log.md), 셀 단위 기록은 [`cell_review.csv`](cell_review.csv), 원시 OCR은 [`raw_ocr.json`](raw_ocr.json)를 참고하세요.
