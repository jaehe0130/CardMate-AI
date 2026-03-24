"""
카드추천 챗봇 - Streamlit 앱 예시
===================================
이 파일은 커스텀 CSS/테마가 적용된 예시 코드입니다.
실제 프로젝트의 main.py에 통합하여 사용하세요.

사용법:
    streamlit run example_main.py
"""

import streamlit as st

# ── 페이지 설정 (반드시 첫 번째로 호출) ──
st.set_page_config(
    page_title="💳 카드추천 챗봇",
    page_icon="💳",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── 커스텀 CSS 주입 ──
from styles.inject_css import (
    inject_custom_css,
    render_hero_section,
    render_recommendation_card,
    render_welcome_message,
    render_sidebar_header,
)

inject_custom_css()

# ── 세션 상태 초기화 ──
if "messages" not in st.session_state:
    st.session_state.messages = []

if "show_welcome" not in st.session_state:
    st.session_state.show_welcome = True

# ── 사이드바 ──
render_sidebar_header()

st.sidebar.divider()

st.sidebar.markdown("### ⚙️ 설정")

# 카테고리 필터
category = st.sidebar.selectbox(
    "관심 카테고리",
    ["전체", "쇼핑", "여행", "카페/음식", "교통", "통신", "문화/여가"],
    index=0,
)

# 연회비 범위
fee_range = st.sidebar.slider(
    "연회비 범위 (만원)",
    min_value=0,
    max_value=30,
    value=(0, 15),
    step=1,
)

# 카드사 선택
card_companies = st.sidebar.multiselect(
    "선호 카드사",
    ["삼성카드", "신한카드", "KB국민카드", "현대카드", "롯데카드", "하나카드", "우리카드", "NH농협카드"],
    default=[],
)

st.sidebar.divider()

# 대화 초기화 버튼
if st.sidebar.button("🗑️ 대화 초기화", use_container_width=True):
    st.session_state.messages = []
    st.session_state.show_welcome = True
    st.rerun()

st.sidebar.divider()

st.sidebar.markdown(
    """
    <div style="text-align: center; padding: 1rem 0;">
        <div style="font-size: 0.75rem; color: #5A5E72;">
            Powered by AI · v1.0.0<br>
            © 2026 CardBot
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

# ── 메인 영역 ──
render_hero_section()

# 탭 구성
tab_chat, tab_recommend, tab_compare = st.tabs(["💬 채팅", "🏆 추천 결과", "📊 카드 비교"])

with tab_chat:
    # 환영 메시지 또는 채팅 내역
    if st.session_state.show_welcome and len(st.session_state.messages) == 0:
        render_welcome_message()
    
    # 채팅 내역 표시
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
    
    # 채팅 입력
    if prompt := st.chat_input("카드 추천이 필요하시면 말씀해주세요..."):
        st.session_state.show_welcome = False
        
        # 사용자 메시지 추가
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)
        
        # AI 응답 (예시 - 실제로는 chatbot.py의 로직 연결)
        with st.chat_message("assistant"):
            with st.spinner("카드를 분석하고 있습니다..."):
                # 여기에 실제 chatbot.py의 추천 로직을 연결하세요
                response = f"""안녕하세요! 말씀하신 내용을 바탕으로 카드를 분석해보았습니다.

**📋 분석 결과:**
- 주요 소비 패턴: 온라인 쇼핑, 카페
- 추천 카테고리: 쇼핑/생활

아래 **🏆 추천 결과** 탭에서 맞춤 카드를 확인해보세요!"""
                st.markdown(response)
        
        st.session_state.messages.append({"role": "assistant", "content": response})

with tab_recommend:
    st.markdown("### 🏆 맞춤 카드 추천")
    st.markdown("*AI가 분석한 최적의 카드 목록입니다*")
    st.markdown("")
    
    # 예시 추천 카드들
    render_recommendation_card(
        card_name="신한카드 Deep Dream",
        card_company="신한카드",
        benefits=["온라인 쇼핑 5%", "스타벅스 50%", "넷플릭스 할인", "교통 10%"],
        annual_fee="1만 5천원",
        match_score=95,
        is_top_pick=True,
    )
    
    render_recommendation_card(
        card_name="삼성카드 taptap O",
        card_company="삼성카드",
        benefits=["간편결제 할인", "온라인 쇼핑 3%", "편의점 할인"],
        annual_fee="1만원",
        match_score=88,
        is_top_pick=False,
    )
    
    render_recommendation_card(
        card_name="KB국민 My WE:SH 카드",
        card_company="KB국민카드",
        benefits=["카페 20%", "배달앱 5%", "OTT 할인", "대중교통 할인"],
        annual_fee="1만 2천원",
        match_score=82,
        is_top_pick=False,
    )
    
    render_recommendation_card(
        card_name="현대카드 ZERO Edition2",
        card_company="현대카드",
        benefits=["전 가맹점 캐시백", "연회비 무료", "포인트 적립"],
        annual_fee="무료",
        match_score=75,
        is_top_pick=False,
    )

with tab_compare:
    st.markdown("### 📊 카드 비교")
    st.markdown("*추천된 카드들의 혜택을 한눈에 비교해보세요*")
    st.markdown("")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric(label="최고 매치율", value="95%", delta="+12%")
    with col2:
        st.metric(label="평균 할인율", value="4.2%", delta="+0.8%")
    with col3:
        st.metric(label="추천 카드 수", value="4장", delta="2장")
    
    st.markdown("")
    st.markdown("---")
    
    # 비교 테이블
    import pandas as pd
    
    comparison_data = {
        "카드명": ["신한 Deep Dream", "삼성 taptap O", "KB My WE:SH", "현대 ZERO Ed.2"],
        "연회비": ["1.5만원", "1만원", "1.2만원", "무료"],
        "쇼핑 혜택": ["⭐⭐⭐⭐⭐", "⭐⭐⭐⭐", "⭐⭐⭐", "⭐⭐⭐"],
        "카페 혜택": ["⭐⭐⭐⭐⭐", "⭐⭐", "⭐⭐⭐⭐⭐", "⭐⭐"],
        "교통 혜택": ["⭐⭐⭐⭐", "⭐⭐⭐", "⭐⭐⭐⭐", "⭐⭐⭐"],
        "매치율": ["95%", "88%", "82%", "75%"],
    }
    
    df = pd.DataFrame(comparison_data)
    st.dataframe(df, use_container_width=True, hide_index=True)
