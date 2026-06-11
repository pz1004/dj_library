from __future__ import annotations

import argparse
import json
from concurrent.futures import ThreadPoolExecutor

import pandas as pd
import requests
from bs4 import BeautifulSoup

_BASE_URL = "https://www.u-library.kr/search/tot/result"
_COLUMNS = ["제목", "청구기호", "도서관명", "대출 가능 여부"]
_EMPTY_DF = pd.DataFrame(columns=_COLUMNS)
_MAX_WORKERS = 8  # 동시 HTTP 요청 상한; 서버 부하와 속도 사이의 균형점


def _parse_books_from_page(soup: BeautifulSoup) -> list[dict[str, str]]:
    """HTML 한 페이지에서 도서 목록을 추출한다."""
    books = []
    for li in soup.find_all("li", id=True):
        title_tag = li.find("dd", class_="dataCheck")
        if title_tag is None:
            continue
        input_tag = title_tag.find("input", {"name": "data"})
        if not (input_tag and "title" in input_tag.attrs):
            continue
        title: str = input_tag["title"]

        call_number_dt = next(
            (dt for dt in li.find_all("dt", class_="title") if dt.get_text(strip=True) == "청구기호"),
            None,
        )
        _call_dd = call_number_dt.find_next_sibling("dd") if call_number_dt else None
        call_number: str = _call_dd.get_text(strip=True) if _call_dd else "정보 없음"

        library_tag = li.find("a", class_="prevAuto", href="#previewLocation")
        if library_tag:
            loan_status_tag = library_tag.find("span", class_="availableBtn")
            if loan_status_tag:
                loan_status = loan_status_tag.text.strip()
                library = library_tag.text.strip().replace(loan_status, "").strip()
            else:
                loan_status = "정보 없음"
                library = library_tag.text.strip()
        else:
            library = "정보 없음"
            loan_status = "정보 없음"

        books.append({"제목": title, "청구기호": call_number, "도서관명": library, "대출 가능 여부": loan_status})
    return books


def fetch_books(keyword: str, library_code: str | None = None) -> pd.DataFrame:
    """키워드로 검색되는 모든 도서를 반환한다 (대출 가능 여부 필터 없음).

    사이트는 검색 결과를 최대 500건으로 제한한다.
    cpp=100 으로 요청하면 최대 5페이지(pn=1~5)이므로, 페이지가 빌 때까지 순회한다.
    """
    base_params: dict[str, str | int] = {"st": "KWRD", "q": keyword, "cpp": 100, "si": 1}
    if library_code:
        base_params["bk_8"] = library_code

    all_books: list[dict[str, str]] = []
    for page in range(1, 6):
        try:
            response = requests.get(
                _BASE_URL, params={**base_params, "pn": page}, timeout=15
            )
        except requests.RequestException as exc:
            print(f"페이지 {page} 요청 실패: {exc}")
            break
        if response.status_code != 200:
            print(f"API 요청 실패: {response.status_code}")
            break
        soup = BeautifulSoup(response.text, "html.parser")
        books_on_page = _parse_books_from_page(soup)
        if not books_on_page:
            break
        all_books.extend(books_on_page)

    return pd.DataFrame(all_books) if all_books else _EMPTY_DF.copy()


def create_total_search_result(
    keywords: list[str] | None,
    library_codes: str | list[str] | None = None,
) -> pd.DataFrame:
    """모든 키워드·도서관 조합으로 검색한 결과를 하나의 평면 DataFrame으로 반환한다.

    반환 콜럼: 제목, 청구기호, 도서관명, 대출 가능 여부
    복수 키워드에서 동일 도서(제목+도서관명)가 중복되면 한 건만 유지한다.
    대출 가능 여부 필터는 적용하지 않는다 — 호출측에서 선택적으로 필터링한다.
    """
    if keywords is None:
        with open("keywords.txt", encoding="utf-8") as f:
            keywords = [line.strip() for line in f if line.strip()]

    if isinstance(library_codes, str):
        library_codes = [library_codes]
    lib_codes: list[str | None] = [None] if library_codes is None else list(library_codes)

    # Build flat argument sequences — same Cartesian order as before, so
    # drop_duplicates keeps the same first-occurrence as the sequential version.
    kw_seq = [kw for lib_code in lib_codes for kw in keywords]
    lc_seq = [lib_code for lib_code in lib_codes for _ in keywords]

    if not kw_seq:
        return _EMPTY_DF.copy()

    with ThreadPoolExecutor(max_workers=min(_MAX_WORKERS, len(kw_seq))) as pool:
        all_data = list(pool.map(fetch_books, kw_seq, lc_seq))

    return (
        pd.concat(all_data, ignore_index=True)
        .drop_duplicates(subset=["제목", "도서관명"])
        .reset_index(drop=True)
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="도서관 도서 대출 가능 여부 확인")
    parser.add_argument("--lib", default=None, type=str, help="도서관명")
    parser.add_argument("--key", nargs="+", default=None, type=str, help="검색어")
    args = parser.parse_args()

    with open("lib_list.json", encoding="utf-8") as f:
        json_data: dict[str, dict[str, str]] = json.load(f)

    library_code: str | None = (
        next(
            (libs[args.lib] for libs in json_data.values() if args.lib in libs),
            None,
        )
        if args.lib
        else None
    )

    results = create_total_search_result(args.key, library_code)
    if results.empty:
        print("검색 결과 없음")
    else:
        available = results[results["대출 가능 여부"] == "대출가능"]
        grouped = (
            available.groupby("도서관명")
            .agg(개수=("제목", "count"), 제목_목록=("제목", list))
            .reset_index()
            .sort_values(by="개수", ascending=False)
        )
        print(grouped)
