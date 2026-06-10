# 대전 공공도서관 도서 검색기 — 개발자 문서

## 프로젝트 개요

대전 공공도서관 통합 검색 사이트([u-library.kr](https://www.u-library.kr))를 HTML 스크래핑하여  
키워드·도서관 조합별 도서 목록과 대출 가능 여부를 수집하고,  
두 가지 웹 프론트엔드(FastAPI, Streamlit)와 CLI를 통해 노출하는 파이썬 패키지입니다.

---

## 디렉터리 구조

```
dj_library/
├── main.py              # 핵심 스크래핑·집계 로직 + CLI 진입점
├── app.py               # FastAPI 웹 서버
├── streamlit_app.py     # Streamlit 웹 앱
├── lib_list.json        # 도서관명 → 내부 코드 매핑 (CLI / Streamlit용)
├── static/
│   └── lib_list.json    # 위와 동일 파일 (FastAPI static 서빙용)
├── templates/
│   └── index.html       # FastAPI Jinja2 템플릿
├── keywords.txt         # CLI 기본 키워드 파일 (줄 단위, 선택적)
└── requirements.txt
```

---

## 의존성

```
streamlit        # Streamlit 프론트엔드
fastapi          # FastAPI 프론트엔드
uvicorn          # ASGI 서버 (FastAPI 실행용)
requests         # HTTP 클라이언트
beautifulsoup4   # HTML 파싱
pandas           # 결과 집계 및 중복 제거
```

Python **3.10+** 필수 (`X | Y` 유니온 구문, `list[...]` 내장 제네릭 사용).

---

## 아키텍처

```
┌─────────────────────────────────────────────┐
│              프론트엔드 계층                  │
│  ┌──────────────┐   ┌────────────────────┐  │
│  │  app.py      │   │  streamlit_app.py  │  │
│  │  (FastAPI)   │   │  (Streamlit)       │  │
│  └──────┬───────┘   └────────┬───────────┘  │
│         │                    │              │
│         └────────┬───────────┘              │
│                  ▼                          │
│           main.py  (비즈니스 로직)           │
│    create_total_search_result()             │
│           │                                │
│    fetch_books()  ×  (키워드 × 도서관)      │
│           │                                │
│    _parse_books_from_page()                │
└─────────────────────────────────────────────┘
                   │  HTTP GET (requests)
                   ▼
         u-library.kr  (외부 사이트)
```

---

## 핵심 모듈 상세: `main.py`

### `_parse_books_from_page(soup) -> list[dict[str, str]]`

| 항목 | 내용 |
|---|---|
| 입력 | `BeautifulSoup` 객체 (단일 페이지 HTML) |
| 출력 | `{"제목": ..., "도서관명": ..., "대출 가능 여부": ...}` 딕셔너리 리스트 |
| 파싱 전략 | `<li id=...>` 항목 순회 → `dd.dataCheck input[name=data]`에서 제목 추출 → `a.prevAuto[href=#previewLocation]` 에서 도서관명·대출 상태 추출 |
| 에러 처리 | 태그 누락 시 `"정보 없음"` 대입 (예외 비전파) |

### `fetch_books(keyword, library_code=None) -> pd.DataFrame`

- `cpp=100`으로 페이지당 최대 100건 요청, `pn=1~5` 페이지 순회 (사이트 최대 500건 제한).
- 빈 페이지를 만나거나 `RequestException` / 비-200 응답 시 조기 종료.
- 결과 없으면 정의된 컬럼을 가진 빈 `_EMPTY_DF` 복사본 반환 — 하위 `pd.concat` 호출 시 스키마 일관성 보장.

### `create_total_search_result(keywords, library_codes=None) -> pd.DataFrame`

| 인수 | 타입 | 설명 |
|---|---|---|
| `keywords` | `list[str] \| None` | `None`이면 `keywords.txt` 파일에서 읽음 |
| `library_codes` | `str \| list[str] \| None` | `None`이면 전체 도서관 검색 (코드 미지정) |

- `library_codes`가 `str`이면 자동으로 `list`로 정규화.
- `lib_codes × keywords` 데카르트 곱으로 `fetch_books` 호출 → `pd.concat` → `drop_duplicates(subset=["제목", "도서관명"])` → `reset_index(drop=True)`.
- **복잡도:** HTTP 요청 수 = `O(|lib_codes| × |keywords| × pages)`, 메모리 = `O(총 행 수)`.

---

## 웹 서버 실행

### FastAPI

```bash
python app.py
# 또는
uvicorn app:app --host 127.0.0.1 --port 8000 --reload
```

- `GET /` — 검색 폼 렌더링 (`index.html`)
- `POST /search` — 폼 데이터 수신, 검색 실행, 결과 HTML 렌더링

**주의:** `app.py`는 모듈 최상위에서 `static/lib_list.json`을 로드합니다.  
작업 디렉터리가 `dj_library/` 루트여야 합니다.

### Streamlit

```bash
streamlit run streamlit_app.py
```

- 세션 상태(`st.session_state`)에 원본 검색 결과(`raw_results`)를 캐시.
- "대출 가능 도서만 보기" 체크박스는 재검색 없이 메모리 내 필터링만 수행.
- `toggle_region(libraries)` — 구 단위 전체 선택/해제. `dict_keys`를 `list`로 한 번만 구체화하여 이중 순회를 방지.

---

## CLI 사용법

```bash
# 전체 도서관, 단일 키워드
python main.py --key 파이썬

# 전체 도서관, 복수 키워드
python main.py --key 파이썬 "데이터 분석" 머신러닝

# 특정 도서관 (도서관명으로 지정)
python main.py --key 파이썬 --lib 한밭도서관

# keywords.txt 사용 (--key 미지정 시 자동 읽기)
python main.py --lib 노은도서관
```

CLI 출력은 `대출가능` 상태 도서만 도서관별로 그룹핑하여 권수 내림차순으로 표시합니다.

---

## 도서관 코드 매핑: `lib_list.json`

```json
{
  "서구": {
    "월평도서관": "H0000027",
    ...
  }
}
```

- 최상위 키: 구 이름 (UI 그룹핑용)
- 중첩 키: 도서관 표시명
- 값: `bk_8` 쿼리 파라미터에 전달되는 내부 식별 코드

`lib_list.json`은 `dj_library/` 루트(CLI·Streamlit용)와 `static/`(FastAPI static 서빙용) 두 곳에 동일하게 존재합니다.  
파일을 수정할 때는 **양쪽 모두** 업데이트하거나, 심볼릭 링크로 단일화하는 것을 권장합니다.

---

## 알려진 제약 및 주의 사항

| 항목 | 내용 |
|---|---|
| 사이트 최대 반환 건수 | 키워드·도서관 조합당 최대 500건 (사이트 정책) |
| HTTP 타임아웃 | 15초 (페이지 단위) |
| 스크래핑 취약성 | u-library.kr HTML 구조 변경 시 파싱 로직(`_parse_books_from_page`) 수정 필요 |
| 병렬 요청 미구현 | 현재 동기 순차 요청. 조합 수가 많으면 `concurrent.futures.ThreadPoolExecutor`로 개선 가능 |
| FastAPI 미들웨어 없음 | CORS, 인증, Rate limiting 미적용. 내부망 또는 개인 사용 전제 |
| `static/lib_list.json` 중복 | 루트와 `static/` 동기화 필요 (위 참조) |

---

## 로컬 개발 환경 구성

```bash
git clone <저장소 주소>
cd dj_library

# 가상 환경 생성 (권장)
python -m venv .venv
.venv\Scripts\activate      # Windows
# source .venv/bin/activate  # macOS/Linux

pip install -r requirements.txt

# FastAPI 개발 서버 (자동 리로드)
uvicorn app:app --reload

# Streamlit
streamlit run streamlit_app.py
```

---

## 테스트 / 문법 검증

현재 공식 테스트 스위트는 없습니다. 최소한의 문법 검증:

```bash
python -m py_compile main.py app.py streamlit_app.py
```

단위 테스트를 추가할 경우 `_parse_books_from_page`에 저장된 HTML 픽스처를 주입하는 방식을 권장합니다.
