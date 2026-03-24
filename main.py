import streamlit as st


def render_sidebar():
    with st.sidebar:
        st.header("조건 설정")

        card_type = st.selectbox(
            "카드 종류",
            ["전체", "신용카드", "체크카드"],
            index=1
        )

        max_base_perf_num = st.selectbox(
            "전월실적 상한",
            [None, 100000, 200000, 300000, 500000],
            index=3,
            format_func=lambda x: "제한 없음" if x is None else f"{x:,}원 이하"
        )

        max_annual_fee_domestic = st.selectbox(
            "국내 연회비 상한",
            [None, 10000, 20000, 30000, 50000],
            index=2,
            format_func=lambda x: "제한 없음" if x is None else f"{x:,}원 이하"
        )

        benefit_categories = st.multiselect(
            "중요 혜택",
            ["편의점", "공과금", "통신비", "카페", "마트", "교통", "주유", "배달"]
        )

    return {
        "card_type": None if card_type == "전체" else card_type,
        "max_base_perf_num": max_base_perf_num,
        "max_annual_fee_domestic": max_annual_fee_domestic,
        "benefit_categories": benefit_categories
    }


def render_chat_messages(messages):
    for msg in messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])


def render_card_list(cards):
    for card in cards:
        col1, col2 = st.columns([1, 2])

        with col1:
            if card.get("image_url"):
                st.image(card["image_url"], use_container_width=True)
            else:
                st.info("이미지 없음")

        with col2:
            st.markdown(f"### {card.get('card_name', '')}")
            st.write(f"카드사: {card.get('company', '')}")
            st.write(f"연회비: {card.get('annual_fee', '')}")
            st.write(f"전월실적: {card.get('base_perf', '')}")
            st.write(f"주요 혜택: {card.get('benefits', '')}")

            if card.get("source_url"):
                st.markdown(f"[상세 보기]({card['source_url']})")

        st.divider()
