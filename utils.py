import streamlit as st


def render_sidebar():
    with st.sidebar:
        st.markdown("## 조건 설정")
        st.caption("채팅 내용과 함께 필터 조건도 반영됩니다.")

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

        st.markdown("---")
        st.markdown("### 사용 팁")
        st.markdown(
            """
- 자주 쓰는 소비처를 먼저 말해보세요  
- 실적 부담, 연회비 부담도 같이 말하면 더 정확해져요  
- 예: `편의점/통신비 위주, 실적 낮은 신용카드`
"""
        )

    return {
        "card_type": None if card_type == "전체" else card_type,
        "max_base_perf_num": max_base_perf_num,
        "max_annual_fee_domestic": max_annual_fee_domestic,
        "benefit_categories": benefit_categories
    }


def render_hero_section():
    st.markdown("""
    <div class="hero-wrap">
        <div class="hero-title">내 소비패턴에 맞는 카드, <br>대화로 쉽게 찾기</div>
        <div class="hero-desc">
            편의점, 통신비, 공과금, 카페, 교통 등 자주 쓰는 소비를 말해주면
            조건에 맞는 카드를 골라드려요.
        </div>
        <span class="hero-chip">생활비 절약형 추천</span>
        <span class="hero-chip">연회비/실적 조건 반영</span>
        <span class="hero-chip">카드 이미지와 함께 비교</span>
    </div>
    """, unsafe_allow_html=True)


def render_quick_prompts():
    st.markdown("### 빠르게 시작하기")

    col1, col2, col3 = st.columns(3)

    selected_prompt = None

    with col1:
        if st.button("생활비 절약형", use_container_width=True):
            selected_prompt = "편의점, 통신비, 공과금 할인 중심으로 생활비 절약에 좋은 신용카드 추천해줘"

    with col2:
        if st.button("카페·편의점형", use_container_width=True):
            selected_prompt = "스타벅스, 카페, 편의점 자주 쓰는 사람에게 좋은 카드 추천해줘"

    with col3:
        if st.button("교통·통신형", use_container_width=True):
            selected_prompt = "대중교통과 통신비 할인에 강한 카드 추천해줘"

    return selected_prompt


def render_preference_summary(user_prefs, sidebar_filters):
    chips = []

    final_card_type = sidebar_filters["card_type"] or user_prefs.get("card_type")
    final_perf = sidebar_filters["max_base_perf_num"] or user_prefs.get("max_base_perf_num")
    final_fee = sidebar_filters["max_annual_fee_domestic"] or user_prefs.get("max_annual_fee_domestic")

    final_benefits = sidebar_filters["benefit_categories"] or user_prefs.get("benefit_categories", [])

    if final_card_type:
        chips.append(f"카드 종류: {final_card_type}")
    if final_perf:
        chips.append(f"전월실적: {final_perf:,}원 이하")
    if final_fee:
        chips.append(f"연회비: {final_fee:,}원 이하")
    for b in final_benefits:
        chips.append(f"혜택: {b}")

    st.markdown('<div class="section-title">현재 반영 조건</div>', unsafe_allow_html=True)
    st.markdown('<div class="pref-box">', unsafe_allow_html=True)

    if chips:
        chip_html = "".join([f'<span class="pref-chip">{chip}</span>' for chip in chips])
        st.markdown(chip_html, unsafe_allow_html=True)
    else:
        st.markdown('<span class="small-muted">아직 조건이 없습니다. 소비 습관이나 원하는 혜택을 말해보세요.</span>', unsafe_allow_html=True)

    st.markdown('</div>', unsafe_allow_html=True)


def render_chat_messages(messages):
    for msg in messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])


def render_card_list(cards):
    cols = st.columns(2)

    for idx, card in enumerate(cards):
        with cols[idx % 2]:
            st.markdown("""
            <div style="
                background:white;
                border:1px solid #eceef5;
                border-radius:22px;
                padding:16px;
                box-shadow:0 6px 20px rgba(20,20,43,0.05);
                margin-bottom:16px;
            ">
            """, unsafe_allow_html=True)

            if card.get("image_url"):
                st.image(card["image_url"], use_container_width=True)
            else:
                st.info("이미지 없음")

            st.markdown(f"### {card.get('card_name', '')}")
            st.markdown(f"**카드사**  \n{card.get('company', '')}")
            st.markdown(f"**연회비**  \n{card.get('annual_fee', '')}")
            st.markdown(f"**전월실적**  \n{card.get('base_perf', '')}")
            st.markdown(f"**주요 혜택**  \n{card.get('benefits', '')}")

            if card.get("source_url"):
                st.markdown(f"[자세히 보기]({card['source_url']})")

            st.markdown("</div>", unsafe_allow_html=True)
