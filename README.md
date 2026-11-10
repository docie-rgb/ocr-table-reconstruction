# OCR 표 이미지 재구성 (AI 교육 선택 과제 B)

> **원본 출처:** 미국 인구조사국(U.S. Bureau of the Census), 1910 인구조사 보고서(1913년 발행), PDF 2쪽 / 인쇄 22쪽, Table 1 — <https://www2.census.gov/library/publications/decennial/1910/volume-1/volume-1-p3.pdf> (과제 안내문 기재 출처, 이미지는 과제 B 자료로 제공받음)

과제에서 제공한 **Census Table 1** 이미지 한 장을 로컬 PC의 CPU에서 **PaddleOCR**로 인식했습니다. 인식한 글자 좌표로 표의 행과 열을 다시 맞춰 `table.csv`와 `document.md`를 만들었고, 원본과 대조한 기록을 함께 남겼습니다.

- 결과물 폴더: [`outputs/ocr/`](outputs/ocr/)
- 재구성 문서: [`outputs/ocr/document.md`](outputs/ocr/document.md)
- 검토 기록(수정 내역, 합계 검증, 원본 대조, 확인 필요): [`outputs/ocr/review_log.md`](outputs/ocr/review_log.md)

## 결과 요약

| 항목 | 결과 |
|---|---|
| 인식한 텍스트 상자 | 41개 (표 제목 1, 머리글 6, 본문 32, 각주 2) |
| 복원한 표 | 데이터 11행 × 3열 (행 이름, 면적, 1910년 인구) + 각주 열 |
| 셀 상태 (33개) | OK 22 · NORMALIZED 8 (공백·점선만 정리) · CORRECTED 2 · BLANK 1 · NEEDS_REVIEW 0 |
| OCR 오인식 수정 | 2건: `17,635,426` → `7,635,426` + 각주¹, `262,810` → `62,810` + 각주² |
| 합계 검증 | 4/4 통과 (전체 = 본토 + 해외 영토, 해외 영토 = 8개 지역의 합, 면적·인구 각각) |
| 원본 직접 대조 | 33개 셀 중 18개 대조, 모두 일치. 나머지 15개는 '미확인'으로 표시 |
| 확인 필요 항목 | 0개 (판독할 수 없는 칸이 없었음. 아래 '범위 정직성' 참고) |

---

## 1. 실행 가능성: 실행 방법과 환경

### 실행 위치와 환경 (기록된 실행 기준, [`manifest.json`](outputs/ocr/manifest.json)에도 기록)

| 항목 | 값 |
|---|---|
| 실행 위치 | 개인 Windows PC에서 로컬 실행 (클라우드나 외부 OCR API는 사용하지 않음) |
| OS | Windows 10 Pro (10.0.19045), x86-64 |
| CPU / 장치 | Intel 64 Family 6 Model 158, 논리 코어 16개 · `device="cpu"` (NVIDIA GPU가 있지만 일부러 쓰지 않음) |
| Python | 3.11.9 (프로젝트 폴더 안 `.venv` 가상환경) |
| 패키지 | paddleocr 3.7.0, paddlepaddle 3.3.1 (CPU), paddlex 3.7.2, opencv-contrib-python 4.10.0.84, numpy 2.3.5, Pillow 13.0.0 |
| OCR 모델 | `PP-OCRv6_medium_det` (글자 위치 검출), `PP-OCRv6_medium_rec` (글자 인식) |
| 처리 시간 | 모델 로드 4~26초 (새 가상환경의 첫 실행이 더 느림), 이미지 1장 인식 18~24초 (CPU) |

### 실행 방법

Python 3.11이 필요하며 명령은 Windows PowerShell 기준입니다. Git Bash에서는 `.venv/Scripts/python`, macOS·Linux에서는 `.venv/bin/python`으로 바꿔 쓰면 됩니다. 저장소에는 기록된 실행 결과가 `outputs/ocr/`에 이미 들어 있어, 실행하지 않아도 결과를 볼 수 있습니다. 다시 실행하면 이 폴더를 지우고 처음부터 다시 만듭니다.

```bash
git clone <이 저장소 URL> ocr-table-reconstruction
```

```bash
cd ocr-table-reconstruction
```

```bash
python -m venv .venv
```

```bash
.venv\Scripts\python -m pip install -r requirements.txt
```

```bash
.venv\Scripts\python scripts/run_pipeline.py --config configs/census_table1.json
```

```bash
.venv\Scripts\python scripts/verify_outputs.py
```

- 처음 실행할 때 PaddleOCR 공식 모델 가중치(두 모델 합쳐 약 140 MB)를 `~/.paddlex/official_models/`에 한 번 내려받습니다. 이때만 인터넷이 필요하고, 인식 자체는 로컬 CPU에서 이뤄집니다.
- `run_pipeline.py`는 `outputs/ocr/`를 지운 뒤 전부 다시 만듭니다. 새 가상환경과 별도 복사본에서 README 절차만으로 재실행해 본 결과, 모든 명령이 정상 종료했고 `table.csv`, `raw_ocr.json`, 검토 기록, 이미지가 기록본과 바이트 단위로 같았습니다(`manifest.json`의 시각·소요 시간만 다름). 다만 이 재실행 때는 모델이 이미 캐시에 있어서, 첫 다운로드 과정은 검증하지 못했습니다.
- `verify_outputs.py`는 필수 파일이 있는지, CSV가 11행·5열 구조인지, 합계 검증과 원본 대조가 모두 통과했는지, 입력 이미지 해시가 맞는지, CPU에서 실행했는지를 확인하고 결과를 PASS/FAIL로 출력합니다.
- 실행 로그에 `����: ...`처럼 깨진 한 줄이 나올 수 있습니다. Paddle이 `ccache`를 찾으려고 Windows `where` 명령을 실행할 때 나오는 한국어(CP949) 메시지로, 결과에는 영향이 없습니다.

### 생성되는 파일 (`outputs/ocr/`)

| 파일 | 내용 |
|---|---|
| `input_census_table1.png` | 입력 이미지 사본 (원본과 SHA-256 동일) |
| `raw_ocr.json` | 원시 OCR 결과: 텍스트, 신뢰도 점수, bbox, 4점 다각형, PaddleOCR 원본 출력 전체 |
| `ocr_boxes.png` | 원본 위에 인식 영역과 상자 번호(#id)를 표시하고, 열별로 색을 나눔. 노란 선은 검출한 표 괘선 |
| `ocr_text_overlay.png` | 왼쪽은 원본과 인식 영역, 오른쪽은 인식한 텍스트를 같은 좌표에 다시 그린 이미지 |
| `table.csv` | 복원한 표 (UTF-8 BOM, 숫자는 쉼표 없는 정수, 공란은 빈 칸) |
| `document.md` | 사람이 읽기 위한 표 문서 (원본 쉼표 표기, 각주, 표기 규칙, 처리 요약) |
| `review_log.md` | 수정 내역, 합계 검증, 원본 직접 대조, 확인 필요 항목 |
| `cell_review.csv` | 셀 33개마다 OCR 원래값, 최종값, 상태, 점수, bbox, OCR 상자 id, 합계·대조 결과 |
| `corrections.json` | 위 검토 내용을 기계가 읽을 수 있게 저장한 파일 |
| `layout.json` | 검출한 괘선 좌표, 열 경계, 헤더·표 하단 y좌표, 행별 OCR 상자 id |
| `crops/` | 셀별 원본 3배 확대 이미지 (원본 대조 근거) |
| `manifest.json` | 이미지 출처·해시, 모델과 설정, 패키지 버전, OS/CPU, 실행 시간, 출력 파일 목록 |

### 코드 구조: OCR과 표 복원을 분리함

```
src/ocrkit/      이미지 → 텍스트 상자 (표에 대해 전혀 모름)
  engine.py      PaddleOCR 래퍼: TextItem(text, score, bbox, poly) 목록 반환
  visualize.py   상자·텍스트 시각화, 확대 크롭, 글리프(잉크) 연결요소 분석
src/tablekit/    텍스트 상자 → 표 (OCR 엔진을 직접 호출하지 않음)
  layout.py      괘선 검출 → 열 경계, 헤더/본문/각주 영역, 행 묶기
  normalize.py   숫자·행 이름 정리 규칙, 위첨자 각주 판별
  reconstruct.py 셀 생성, 수정, 합계 검증, 원본 대조 반영
  export.py      table.csv, document.md, review_log.md, cell_review.csv
scripts/run_pipeline.py   전체 실행 (설정: configs/census_table1.json)
scripts/verify_outputs.py 결과물 검증
review/manual_checks.json 사람이 원본에서 읽은 값 (파이프라인 입력)
```

---

## 2. 원본 대조와 근거

결과를 원본과 세 가지 방법으로 맞춰 보았고, 모든 내용은 [`review_log.md`](outputs/ocr/review_log.md)에 원본 좌표와 함께 남겼습니다.

1. **모든 셀을 원본 위치와 연결.** CSV의 셀마다 어떤 OCR 상자(`ocr_item_ids`)에서 왔는지, 원본의 어느 위치(`bbox`, 픽셀 좌표)에 있는지를 [`cell_review.csv`](outputs/ocr/cell_review.csv)에 기록했습니다. `ocr_boxes.png`에서 같은 번호의 상자를 찾으면 원본 위치를 바로 볼 수 있습니다.
2. **원본 직접 대조 (18개 셀).** 파이프라인이 bbox로 원본을 잘라 3배 확대한 이미지(`outputs/ocr/crops/`)를 눈으로 읽은 값을 [`review/manual_checks.json`](review/manual_checks.json)에 적었습니다. 파이프라인은 이 값을 CSV와 자동으로 비교합니다. 대조한 셀은 합계 행, 해외 영토 소계, Alaska 행 전체, Samoa 행 전체, 공란 칸, 각주가 붙은 두 숫자처럼 결과에 영향이 큰 셀들입니다. 18개 모두 일치했습니다.
   - 판독은 이 과제를 함께 수행한 AI 보조(Claude)가 했습니다. 사람 검토자가 아니므로 제출 전에 과제 수행자가 같은 확대 이미지로 다시 확인하는 것을 권장합니다. 이 내용은 검토 기록에도 적어 두었습니다.
3. **합계 검증.** 원본 표 안의 덧셈 관계를 이용했습니다. 전체 = 본토 + 해외 영토, 해외 영토 = 8개 지역의 합이며, 면적과 인구를 각각 확인해 4개 검증이 모두 맞았습니다. 각주 숫자를 떼어내지 않았다면 인구 소계가 10,000,000 + 200,000만큼 어긋났을 것이고, 이 검증이 그 오류를 잡아내는 장치입니다.

### OCR 오인식 수정 내역

| 위치 | OCR 원래값 | 수정값 | 근거 |
|---|---|---|---|
| 8행 Philippine Islands, 인구 (bbox 921,340–1035,365) | `17,635,426` | `7,635,426` + 각주 1 | 첫 글자 `1`의 하단이 숫자 기준선보다 7px 위에 있고, 높이도 10px로 숫자 높이 17px보다 작은 위첨자입니다. 표 아래 각주 "¹ Population in 1903."과 번호가 같습니다. 수정 후 해외 영토 인구 합계가 9,143,221로 맞습니다. |
| 9행 Panama Canal Zone, 인구 (bbox 952,363–1035,388) | `262,810` | `62,810` + 각주 2 | 첫 글자 `2`가 기준선보다 6px 위에 있고 높이가 11px(숫자 16px)인 위첨자입니다. 각주 "² Population in 1912."와 번호가 같고, 수정 후 합계가 맞습니다. |

이 수정은 사람이 손으로 고친 것이 아닙니다. `normalize.superscript_prefix`가 글자 모양을 측정해 위첨자를 판별하고, 그 판별과 표 아래 각주 번호가 모두 맞을 때만 자동으로 적용합니다. 같은 규칙으로 `1`이나 `2`로 시작하는 다른 숫자 4개(`101,115,487`, `191,909`, `1,118,012`, `210`)도 검사했지만, 위첨자가 아니어서 그대로 두었습니다.

표기 정리는 8건이며 내용은 바꾸지 않았습니다. 숫자 안의 공백을 없앴고(`101, 115, 487` → `101,115,487`, 원본 인쇄에 쉼표 뒤 공백이 있음), 행 이름 끝에 붙은 점선 리더 조각을 지웠습니다(`Alaska.` → `Alaska`). 전체 목록은 `review_log.md` 1절에 있습니다.

---

## 3. 범위 정직성: 처리한 범위, 미확인 부분, 실패

- **처리 범위:** 과제에서 받은 Census Table 1 이미지 한 장만 처리했습니다. 함께 받은 다른 표 이미지(Federal Reserve "No. 11")는 처리하지 않았고 저장소에도 넣지 않았습니다.
- **공란은 추측으로 채우지 않음:** "Military and naval service abroad" 행의 면적 칸은 원본에 점선만 있고 숫자가 없습니다. CSV에서는 빈 칸, `document.md`에서는 `—`로 두었고 0으로 채우지 않았습니다. 합계 검증에서도 이 칸은 계산에서 빼고, 뺐다는 사실을 기록했습니다.
- **판독 불가 처리 규칙:** 숫자 형식이 맞지 않거나 판독할 수 없으면 값을 `확인 필요`로 두고 OCR 원래값을 `review_log.md` 4절에 남기도록 구현했습니다. 이번 이미지에서는 이 규칙에 걸린 칸이 없었습니다. OCR 점수가 가장 낮은 것도 0.936(`Hawaii.`)으로, 저신뢰 기준 0.90보다 높았습니다.
- **미확인으로 남긴 부분:**
  - 직접 대조하지 않은 셀 15개는 `cell_review.csv`의 `manual_check=not_checked`로 표시했습니다. 숫자 셀은 합계 검증으로만, 행 이름 셀은 OCR 점수로만 뒷받침됩니다.
  - 표 머리글 3개와 표 아래 각주 문장 2개는 셀 대조 대상에 넣지 않았습니다.
  - 출처(PDF 2쪽, 인쇄 22쪽)는 과제 안내문에 적힌 값입니다. 해당 PDF를 직접 받아 이미지와 대조하지는 않았습니다 ([`data/input/SOURCE.md`](data/input/SOURCE.md)).
  - 사람 검토를 요청한 6개 셀(`review_log.md` 3-1절)은 과제 수행자가 확인하기 전까지 상태가 `pending`이며, 사람이 검증한 것으로 기록하지 않았습니다.
  - 원본 대조는 AI 보조가 했으며, 사람이 대조한 것은 아닙니다.
- **복원하지 않은 정보:** 행의 들여쓰기 계층(본토/해외 영토 아래 하위 지역), 굵은 글씨, 이중 괘선은 CSV에 넣지 않았습니다. 계층 관계는 `configs/census_table1.json`의 합계 검증 정의에만 반영되어 있습니다.
- **실행 중 겪은 오류:** PaddlePaddle 3.3.1의 Windows CPU 환경에서 oneDNN을 켜면 `NotImplementedError: ConvertPirAttribute2RuntimeAttribute not support`가 나면서 인식이 실패했습니다. `enable_mkldnn=False`로 해결했고, 대신 속도가 다소 느려졌습니다.
- **일반화 한계:** 열 경계는 이미지의 세로 괘선으로 정합니다. 괘선이 없는 표에서는 열을 나누는 대체 방법이 아직 구현되어 있지 않아 설정 오류(`ValueError`)로 멈춥니다. 합계 검증에 쓰는 행 이름도 이 표에 맞춰 설정 파일에 직접 적었습니다. 다른 OCR 엔진(Tesseract 등)과 비교 실험은 하지 않았습니다.

---

## 4. 설명: 실행 위치와 도구·설정 선택 이유

| 선택 | 이유 (작업 목적과 실제 결과에 연결) |
|---|---|
| 로컬 Windows PC, CPU 실행 | 과제 조건(외부 OCR API 금지, CPU 우선)을 따랐습니다. GPU 없이도 이미지 1장을 약 18초에 처리해, 한 장짜리 과제에는 충분했습니다. 다른 사람도 GPU 없이 같은 결과를 재현할 수 있습니다. |
| PaddleOCR 3.7 (PP-OCRv6 det + rec) | 설치만 하면 오프라인으로 인식하고, 글자마다 **좌표(다각형·bbox)와 신뢰도 점수**를 함께 줍니다. 표 복원과 원본 대조는 결국 좌표가 근거이므로 이 기능이 꼭 필요했습니다. 실제로 숫자 셀 21개 가운데 위첨자가 붙은 2개를 빼면 모두 정확히 읽었고, 셀 33개 전체의 최저 점수는 0.936이었습니다. |
| `lang="en"` | 원본이 영어 활자이고 숫자와 쉼표가 대부분이기 때문입니다. |
| 문서 방향·왜곡 보정·텍스트라인 방향 모델 끔 | 스캔 이미지가 똑바로 놓여 있고 휘지 않아서 필요 없었습니다. 끄면 모델 3개를 덜 받고 처리도 빨라집니다. |
| `enable_mkldnn=False` | 위에서 설명한 oneDNN 오류를 피하기 위한 설정입니다. 끄지 않으면 결과가 하나도 나오지 않았습니다. |
| `text_rec_score_thresh=0.0`, 저신뢰 기준 0.90 | OCR 단계에서 아무 결과도 버리지 않고 모두 원시 JSON에 남긴 뒤, 점수가 낮은 것은 검토 단계에서 `확인 필요`로 표시하기 위해서입니다. 결과를 숨기지 않으려는 선택입니다. |
| 표 구조는 PP-Structure 같은 표 인식 모델 대신 괘선 검출 + 좌표 규칙으로 복원 | 셀마다 "어느 OCR 상자에서, 원본 어느 좌표에서 왔는가"를 하나씩 추적하기 위해서입니다. 이 표는 세로 괘선 2개(x≈670, 855)와 가로 괘선(헤더 아래 y≈97, 표 하단 y≈456)이 뚜렷해 규칙만으로 11행 × 3열을 정확히 나눌 수 있었습니다. |
| 위첨자 판별 + 각주 번호 + 합계 검증 | OCR이 실제로 틀린 지점(각주 번호가 숫자에 붙어 읽힘)을 근거 있게 고치기 위해서입니다. 세 근거가 서로 독립적이어서, 하나만 쓸 때보다 수정이 틀릴 위험이 낮습니다. |
| OCR(`ocrkit`)과 표 복원(`tablekit`)을 분리 | OCR 층은 표에 대해 아무것도 모르게 만들어, 표가 아닌 이미지에도 그대로 다시 쓸 수 있게 했습니다. |

**향후 확장:** `ocrkit`은 표와 무관하게 이미지에서 텍스트와 좌표만 돌려주므로, 앞으로 만화 말풍선 OCR과 로컬 번역 파이프라인의 입력 단계로 다시 쓸 계획입니다. 이번 제출에는 그 기능이 들어 있지 않습니다.

---

## 공개 범위

저장소에는 코드, 설정, 과제가 제공한 표 이미지 한 장, 그 이미지로 만든 결과물만 들어 있습니다. `manifest.json`의 경로는 사용자 홈 폴더를 `~`로 바꿔 기록했고, 계정·개인 정보는 넣지 않았습니다.
