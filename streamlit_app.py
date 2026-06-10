import json
import streamlit as st
from main import create_total_search_result

st.set_page_config(page_title="도서 검색", layout="wide")
st.title("📚 대전 공공도서관 대출가능 도서 검색")

# Load library list
with open("lib_list.json", "r", encoding="utf-8") as f:
    lib_list = json.load(f)

# Initialise session-state keys for every library checkbox (runs once per session)
for region, libraries in lib_list.items():
    for lib_code in libraries.values():
        key = f"lib_{lib_code}"
        if key not in st.session_state:
            st.session_state[key] = False


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

# ── Search button ────────────────────────────────────────────────────────────
st.divider()
if st.button("🔍 검색", type="primary"):
    if not keywords_input.strip():
        st.warning("키워드를 입력해 주세요.")
    else:
        keywords_list = [k.strip() for k in keywords_input.splitlines() if k.strip()]
        codes = selected_codes if selected_codes else None

        n_requests = len(keywords_list) * (len(codes) if codes else 1)
        if n_requests > 20:
            st.warning(
                f"⚠️ {n_requests}회 요청 예정입니다. 완료까지 수 분이 걸릴 수 있습니다."
            )

        with st.spinner(f"검색 중... ({n_requests}회 요청)"):
            try:
                results = create_total_search_result(keywords_list, codes)
            except Exception as e:
                st.error(f"검색 중 오류가 발생했습니다: {e}")
                st.stop()

        if results.empty:
            st.info("대출 가능한 도서가 없습니다.")
        else:
            total_books = int(results['개수'].sum())
            st.subheader(f"검색 결과 — {total_books}권 / {len(results)}개 도서관")
            for _, row in results.iterrows():
                with st.expander(f"{row['도서관']} — {row['개수']}권"):
                    for title in row['대출 가능 도서']:
                        st.write(f"- {title}")
