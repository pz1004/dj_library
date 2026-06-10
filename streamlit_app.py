import json
import streamlit as st
from main import create_total_search_result

st.set_page_config(page_title="도서 검색", layout="wide")
st.title("📚 대전 공공도서관 도서 검색")

# Load library list
with open("lib_list.json", "r", encoding="utf-8") as f:
    lib_list = json.load(f)

# 첫 로딩 시 세션 상태 초기화
for region, libraries in lib_list.items():
    for lib_code in libraries.values():
        key = f"lib_{lib_code}"
        if key not in st.session_state:
            st.session_state[key] = False

if "raw_results" not in st.session_state:
    st.session_state["raw_results"] = None


def toggle_region(libraries: dict) -> None:
    """Toggle all checkboxes in a region: select all if any is unselected, else deselect all."""
    all_selected = all(st.session_state.get(f"lib_{code}", False) for code in libraries.values())
    for lib_code in libraries.values():
        st.session_state[f"lib_{lib_code}"] = not all_selected


# ── Keywords input ──────────────────────────────────────────────────────────
keywords_input = st.text_area(
    "키워드 (한 줄에 하나씩 입력)",
    height=120,
    placeholder="예:\n파이썬\n데이터 분석",
)

# ── Library checkboxes grouped by region ────────────────────────────────────
st.subheader("도서관 선택")
st.caption("도서관을 선택하지 않으면 전체 도서관을 대상으로 검색합니다.")

regions = list(lib_list.items())
cols = st.columns(3)
for i, (region, libraries) in enumerate(regions):
    with cols[i % 3]:
        st.markdown(f"**{region}**")
        st.button(
            "전체 선택/해제",
            key=f"btn_{region}",
            on_click=toggle_region,
            args=(libraries,),
        )
        for lib_name, lib_code in libraries.items():
            st.checkbox(lib_name, key=f"lib_{lib_code}")

# Collect selected library codes after widgets are rendered
selected_codes = [
    lib_code
    for libraries in lib_list.values()
    for lib_name, lib_code in libraries.items()
    if st.session_state.get(f"lib_{lib_code}", False)
]

# ── Search button + filter checkbox ────────────────────────────────────────
st.divider()
col_btn, col_chk = st.columns([1, 3])
with col_btn:
    search_clicked = st.button("🔍 검색", type="primary")
with col_chk:
    # 체크박스 변경 시 재검색 없이 기존 결과에서 필터만 다시 적용
    available_only = st.checkbox("대출 가능 도서만 보기", value=True)

if search_clicked:
    if not keywords_input.strip():
        st.warning("키워드를 입력해 주세요.")
    else:
        keywords_list = [k.strip() for k in keywords_input.splitlines() if k.strip()]
        codes = selected_codes if selected_codes else None

        # 실제 요청 횟수: 조합당 최대 5페이지(페이지당 100건)
        n_combos = len(keywords_list) * (len(codes) if codes else 1)
        if n_combos > 10:
            st.warning(
                f"⚠️ 검색 조합이 {n_combos}개입니다. "
                f"조합당 최대 5페이지(각 100건)를 추가 요청하므로 "
                f"최대 {n_combos * 5}회 HTTP 요청이 발생할 수 있습니다."
            )

        lib_desc = f"도서관 {len(codes)}개" if codes else "전체 도서관"
        with st.spinner(f"검색 중... (키워드 {len(keywords_list)}개 × {lib_desc})"):
            try:
                results = create_total_search_result(keywords_list, codes)
                st.session_state["raw_results"] = results
            except Exception as e:
                st.error(f"검색 중 오류가 발생했습니다: {e}")
                st.stop()

# ── Display: checkbox 변경 시 재검색 없이 메모리에서 필터링 ──────────────────
raw = st.session_state.get("raw_results")
if raw is not None:
    df = raw[raw['대출 가능 여부'] == '대출가능'] if available_only else raw

    if df.empty:
        st.info("대출 가능한 도서가 없습니다." if available_only else "검색 결과가 없습니다.")
    else:
        grouped = (
            df.groupby('도서관명')
            .agg(개수=('제목', 'count'), 도서_목록=('제목', list))
            .reset_index()
            .sort_values(by='도서관명', ascending=True)
        )
        label = "대출가능" if available_only else "전체"
        total_books = int(grouped['개수'].sum())
        st.subheader(f"검색 결과 ({label}) — {total_books}권 / {len(grouped)}개 도서관")
        for _, row in grouped.iterrows():
            with st.expander(f"{row['도서관명']} — {row['개수']}권"):
                for title in row['도서_목록']:
                    st.write(f"- {title}")

