import requests
from bs4 import BeautifulSoup
import pandas as pd
import argparse
import json

_EMPTY_DF = pd.DataFrame(columns=['제목', '도서관명', '대출 가능 여부'])


def _parse_books_from_page(soup):
    """HTML 한 페이지에서 도서 목록을 추출한다."""
    books = []
    for li in soup.find_all('li', id=True):
        title_tag = li.find('dd', class_='dataCheck')
        if title_tag is None:
            continue
        input_tag = title_tag.find('input', {'name': 'data'})
        if not (input_tag and 'title' in input_tag.attrs):
            continue
        title = input_tag['title']

        library_tag = li.find('a', class_='prevAuto', href='#previewLocation')
        if library_tag:
            library = library_tag.text.strip()
            loan_status_tag = library_tag.find('span', class_='availableBtn')
            loan_status = loan_status_tag.text.strip() if loan_status_tag \
                else '정보 없음'
            library = library.replace(loan_status, '').strip()
        else:
            library = '정보 없음'
            loan_status = '정보 없음'

        books.append({'제목': title, '도서관명': library, '대출 가능 여부': loan_status})
    return books


def fetch_books(keyword, library_code=None):
    """키워드로 검색되는 모든 도서를 반환한다 (대출 가능 여부 필터 없음).

    사이트는 검색 결과를 최대 500건으로 제한한다.
    cpp=100 으로 요청하면 최대 5페이지(pn=1~5)이므로, 페이지가 빌 때까지 순회한다.
    """
    base_url = (
        "https://www.u-library.kr/search/tot/result?st=KWRD"
        f"&q={keyword}&cpp=100&si=1"
    )
    if library_code:
        base_url += f"&bk_8={library_code}"

    all_books = []
    # 사이트 최대 500건 ÷ cpp=100 = 5 페이지
    for page in range(1, 6):
        try:
            response = requests.get(base_url + f"&pn={page}", timeout=15)
        except requests.Timeout:
            print(f"페이지 {page} 요청 시간 초과")
            break
        if response.status_code != 200:
            print(f"API 요청 실패: {response.status_code}")
            break
        soup = BeautifulSoup(response.text, 'html.parser')
        books_on_page = _parse_books_from_page(soup)
        if not books_on_page:
            break  # 더 이상 결과 없음
        all_books.extend(books_on_page)

    return pd.DataFrame(all_books) if all_books else _EMPTY_DF.copy()


def create_total_search_result(keywords, library_codes=None):
    """모든 키워드·도서관 조합으로 검색한 결과를 하나의 평면 DataFrame으로 반환한다.

    반환 컬럼: 제목, 도서관명, 대출 가능 여부
    복수 키워드에서 동일 도서(제목+도서관명)가 중복되면 한 건만 유지한다.
    대출 가능 여부 필터는 적용하지 않는다 — 호출측에서 선택적으로 필터링한다.
    """
    all_data = []

    if keywords is None:
        with open("keywords.txt", "r", encoding='utf-8') as f:
            keywords = [line.strip() for line in f if line.strip()]

    if library_codes is None:
        for keyword in keywords:
            all_data.append(fetch_books(keyword))
    else:
        if isinstance(library_codes, str):
            library_codes = [library_codes]
        for library_code in library_codes:
            for keyword in keywords:
                all_data.append(fetch_books(keyword, library_code))

    if not all_data:
        return _EMPTY_DF.copy()

    combined_df = pd.concat(all_data, ignore_index=True)
    # 복수 키워드 검색에서 동일 도서가 중복되면 제거
    combined_df = combined_df.drop_duplicates(subset=['제목', '도서관명'])
    return combined_df


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='도서관 도서 대출 가능 여부 확인')
    parser.add_argument('--lib', default=None, type=str, help='도서관명')
    parser.add_argument('--key', nargs="+", default=None, type=str, help='검색어')
    args = parser.parse_args()
    with open("lib_list.json", "r", encoding='utf-8') as f:
        json_data = json.load(f)
    library_code = None
    if args.lib:
        for key, value in json_data.items():
            a = value.get(args.lib)
            if a:
                library_code = a
                break

    results = create_total_search_result(args.key, library_code)
    if results.empty:
        print("검색 결과 없음")
    else:
        available = results[results['대출 가능 여부'] == '대출가능']
        grouped = (
            available.groupby('도서관명')
            .agg(개수=('제목', 'count'), 제목_목록=('제목', list))
            .reset_index()
            .sort_values(by='개수', ascending=False)
        )
        print(grouped)
