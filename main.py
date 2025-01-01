import requests
from bs4 import BeautifulSoup
import pandas as pd
import argparse
import json


def fetch_books(keyword, library_code=None):
    # API 요청 URL
    base_url = "https://www.u-library.kr/search/tot/result?st=KWRD"
    base_url += f"&q={keyword}"
    # 한 페이지당 출력 개수
    # 5, 10, 15, 20, 30, 50, 100 중 선택 가능
    base_url += "&cpp=50"
    # 검색 기준
    # TOTAL: 전체, 1: 서명, 2: 저자, 3: 출판사, 4: 주제어
    base_url += "&si=1"

    if library_code:
        base_url += f"&bk_8={library_code}"
    # API 요청
    response = requests.get(base_url)
    if response.status_code != 200:
        print(f"API 요청 실패: {response.status_code}")
        return pd.DataFrame()

    # BeautifulSoup을 이용한 HTML 파싱
    soup = BeautifulSoup(response.text, 'html.parser')

    # 데이터를 저장할 리스트
    books = []

    # <li> 태그를 모두 찾음
    li_tags = soup.find_all('li', id=True)

    for li in li_tags:
        # 제목 가져오기
        title_tag = li.find('dd', class_='dataCheck')
        input_tag = title_tag.find('input', {'name': 'data'})
        if input_tag and 'title' in input_tag.attrs:
            title = input_tag['title']
        else:
            print("title 속성이 없습니다.")
            continue

        # 도서관명 가져오기
        library_tag = li.find('a', class_='prevAuto', href='#previewLocation')
        if library_tag:
            library = library_tag.text.strip()
            loan_status_tag = library_tag.find('span', class_='availableBtn')
            loan_status = loan_status_tag.text.strip() if loan_status_tag else '정보 없음'
            library = library.replace(loan_status, '')
        else:
            library = '정보 없음'
            loan_status = '정보 없음'

        # 데이터 추가
        books.append({
            '제목': title,
            '도서관명': library,
            '대출 가능 여부': loan_status
        })

    # DataFrame으로 변환
    books_df = pd.DataFrame(books)
    print(books_df.head())

    # 대출 가능 도서만 필터링
    available_books = books_df[books_df['대출 가능 여부'] == '대출가능']
    return available_books


def create_total_search_result(keywords, library_codes=None):
    all_data = []

    if keywords is None:
        with open("keywords.txt", "r", encoding='utf-8') as f:
            keywords = f.readlines()
            keywords = [keyword.strip() for keyword in keywords]

    if library_codes is None:
        for keyword in keywords:
            df = fetch_books(keyword)
            all_data.append(df)
    else:
        if isinstance(library_codes, str):
            library_codes = [library_codes]
        for library_code in library_codes:
            for keyword in keywords:
                df = fetch_books(keyword, library_code)
                all_data.append(df)

    # 모든 검색 결과를 하나의 DataFrame으로 합침
    combined_df = pd.concat(all_data, ignore_index=True)

    # 결과 정리
    total_search_result = (
        combined_df.groupby('도서관명')
        .agg(
            개수=('제목', 'count'),
            대출_가능_도서=('제목', list)
        )
        .reset_index()
        .sort_values(by='개수', ascending=False)
    )
    total_search_result.rename(columns={'도서관명': '도서관', '대출_가능_도서': '대출 가능 도서'}, inplace=True)

    print(total_search_result)
    return total_search_result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='도서관 도서 대출 가능 여부 확인')
    parser.add_argument('--lib', default=None, type=str, help='도서관명')
    parser.add_argument('--key', nargs="+", default=None, type=str, help='검색 키워드')
    args = parser.parse_args()
    with open("lib_list.json", "r", encoding='utf-8') as f:
        json_data = json.load(f)
    for key, value in json_data.items():
        a = value.get(args.lib)
        if a:
            print(key, a)
            break
    create_total_search_result(args.key, a)
