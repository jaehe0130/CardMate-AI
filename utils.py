import streamlit as st


def render_sidebar():
    with st.sidebar:
        st.markdown("## CardMate AI")
        st.caption("상담 조건을 설정하면 추천 정확도가 높아집니다.")

        st.markdown("### 카드 조건")
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

        st.markdown("### 주요 혜택")
        benefit_categories = st.multiselect(
            "자주 쓰는 소비처",
            ["편의점", "공과금", "통신비", "카페", "마트", "교통", "주유", "배달"]
        )

        st.markdown("---")
        st.markdown("### 상담 예시")
        st.markdown(
            """
- 편의점, 통신비 위주 카드 추천  
- 연회비 부담 적은 신용카드 추천  
- 공과금이랑 교통 혜택 좋은 카드 추천  
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
        <div class="hero-badge">Premium Card Recommendation</div>
        <div class="hero-title">
            내 소비에 맞는 카드,<br>
            상담받듯 정교하게 추천
        </div>
        <div class="hero-desc">
            편의점, 통신비, 공과금, 카페, 교통처럼 자주 쓰는 소비를 알려주면
            실적 부담과 연회비 조건까지 반영해 카드 후보를 정리해드립니다.
        </div>
        <span class="hero-chip">생활비 절약형 추천</span>
        <span class="hero-chip">실적·연회비 조건 반영</span>
        <span class="hero-chip">카드 이미지와 함께 비교</span>
    </div>
    """, unsafe_allow_html=True)


def render_service_notice():
    st.markdown("""
    <div class="notice-box">
        <div class="notice-title">추천 방식 안내</div>
        <div class="notice-desc">
            대화 내용과 필터 조건을 함께 반영해 카드를 추리고,
            추천 이유와 함께 비교가 쉽도록 정리해드립니다.
        </div>
    </div>
    """, unsafe_allow_html=True)


def render_quick_actions():
    st.markdown('<div class="surface-card quick-btn-wrap">', unsafe_allow_html=True)
    st.markdown('<div class="section-title">빠른 추천 시작</div>', unsafe_allow_html=True)

    col1, col2, col3 = st.columns(3)
    selected_prompt = None

    with col1:
        if st.button("생활비 절약형", use_container_width=True):
            selected_prompt = "편의점, 공과금, 통신비 할인 중심으로 생활비 절약에 좋은 신용카드 추천해줘"

    with col2:
        if st.button("카페·편의점형", use_container_width=True):
            selected_prompt = "스타벅스, 카페, 편의점을 자주 쓰는 사람에게 좋은 카드 추천해줘"

    with col3:
        if st.button("교통·통신형", use_container_width=True):
            selected_prompt = "대중교통과 통신비 할인에 강한 신용카드 추천해줘"

    st.markdown('</div>', unsafe_allow_html=True)
    return selected_prompt


def render_preference_summary(user_prefs, sidebar_filters):
    chips = []

    final_card_type = sidebar_filters["card_type"] or user_prefs.get("card_type")
    final_perf = sidebar_filters["max_base_perf_num"] or user_prefs.get("max_base_perf_num")
    final_fee = sidebar_filters["max_annual_fee_domestic"] or user_prefs.get("max_annual_fee_domestic")
    final_benefits = sidebar_filters["benefit_categories"] or user_prefs.get("benefit_categories", [])

    st.markdown('<div class="section-title">현재 반영 조건</div>', unsafe_allow_html=True)

    if final_card_type:
        chips.append(f"카드 종류 · {final_card_type}")
    if final_perf:
        chips.append(f"전월실적 · {final_perf:,}원 이하")
    if final_fee:
        chips.append(f"연회비 · {final_fee:,}원 이하")
    for b in final_benefits:
        chips.append(f"혜택 · {b}")

    if chips:
        chip_html = "".join([f'<span class="pref-chip">{chip}</span>' for chip in chips])
        st.markdown(f'<div class="pref-wrap">{chip_html}</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="subtle-text">아직 반영된 조건이 없습니다. 원하는 소비 혜택이나 부담스러운 조건을 말해보세요.</div>', unsafe_allow_html=True)


def render_chat_messages(messages):
    for msg in messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])


def render_card_list(cards):
    cols = st.columns(2)

    for idx, card in enumerate(cards):
        with cols[idx % 2]:
            st.markdown('<div class="card-shell">', unsafe_allow_html=True)
            st.markdown('<div class="card-top-badge">추천 카드</div>', unsafe_allow_html=True)

            if card.get("image_url"):
                st.image(card["image_url"], use_container_width=True)
            else:
                st.info("이미지 없음")

            st.markdown(f'<div class="card-title">{card.get("card_name", "")}</div>', unsafe_allow_html=True)

            meta_text = f"""
카드사: {card.get('company', '')}<br>
연회비: {card.get('annual_fee', '')}<br>
전월실적: {card.get('base_perf', '')}
"""
            st.markdown(f'<div class="card-meta">{meta_text}</div>', unsafe_allow_html=True)

            st.markdown(
                f'<div class="card-benefit">{card.get("benefits", "")}</div>',
                unsafe_allow_html=True
            )

            if card.get("source_url"):
                st.markdown(
                    f'<div class="card-link" style="margin-top:12px;"><a href="{card["source_url"]}" target="_blank">상품 상세 보기</a></div>',
                    unsafe_allow_html=True
                )

            st.markdown('</div>', unsafe_allow_html=True)
