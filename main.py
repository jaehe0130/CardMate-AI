import streamlit as st

# ──────────────────────────────────────────────
# 페이지 설정
# ──────────────────────────────────────────────
st.set_page_config(
    page_title="미리은행 카드추천 챗봇",
    page_icon="💳",
    layout="centered",
    initial_sidebar_state="collapsed",
)

# ──────────────────────────────────────────────
# 커스텀 CSS (미리은행 스타일 – 파란색/흰색 테마)
# ──────────────────────────────────────────────
st.markdown(
    """
    <style>
    /* ── 전역 ── */
    @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;500;700;900&display=swap');

    .stApp {
        background: linear-gradient(180deg, #3B82F6 0%, #60A5FA 40%, #F0F7FF 40%);
        font-family: 'Noto Sans KR', sans-serif;
    }

    /* 사이드바 숨기기 */
    [data-testid="stSidebar"] { display: none; }

    /* ── 헤더 영역 ── */
    .header-area {
        background: linear-gradient(135deg, #2563EB 0%, #3B82F6 50%, #60A5FA 100%);
        border-radius: 0 0 32px 32px;
        padding: 32px 24px 40px 24px;
        text-align: center;
        margin: -1rem -1rem 0 -1rem;
        position: relative;
        overflow: hidden;
    }
    .header-area::before {
        content: '';
        position: absolute;
        top: -40px; right: -40px;
        width: 160px; height: 160px;
        background: rgba(255,255,255,0.08);
        border-radius: 50%;
    }
    .header-area::after {
        content: '';
        position: absolute;
        bottom: -20px; left: 30px;
        width: 100px; height: 100px;
        background: rgba(255,255,255,0.06);
        border-radius: 50%;
    }
    .header-logo {
        font-size: 14px;
        font-weight: 700;
        color: rgba(255,255,255,0.85);
        letter-spacing: 2px;
        margin-bottom: 8px;
    }
    .header-title {
        font-size: 28px;
        font-weight: 900;
        color: #FFFFFF;
        margin: 0;
        line-height: 1.3;
        text-shadow: 0 2px 8px rgba(0,0,0,0.15);
    }
    .header-subtitle {
        font-size: 15px;
        color: rgba(255,255,255,0.9);
        margin-top: 8px;
        font-weight: 500;
    }
    .header-badge {
        display: inline-block;
        background: rgba(255,255,255,0.2);
        backdrop-filter: blur(4px);
        border: 1px solid rgba(255,255,255,0.3);
        border-radius: 20px;
        padding: 6px 16px;
        font-size: 12px;
        color: #fff;
        margin-top: 16px;
        font-weight: 500;
    }

    /* ── 카드 컨테이너 ── */
    .card-container {
        background: #FFFFFF;
        border-radius: 20px;
        padding: 24px;
        margin: 20px 0;
        box-shadow: 0 4px 24px rgba(59,130,246,0.10), 0 1px 4px rgba(0,0,0,0.04);
        border: 1px solid #E8F0FE;
    }
    .card-container h3 {
        color: #1E3A5F;
        font-size: 18px;
        font-weight: 700;
        margin-bottom: 16px;
        display: flex;
        align-items: center;
        gap: 8px;
    }

    /* ── 챗봇 메시지 ── */
    .chat-wrapper {
        background: #FFFFFF;
        border-radius: 20px;
        padding: 20px;
        margin: 16px 0;
        box-shadow: 0 4px 24px rgba(59,130,246,0.10), 0 1px 4px rgba(0,0,0,0.04);
        border: 1px solid #E8F0FE;
        max-height: 420px;
        overflow-y: auto;
    }
    .bot-msg {
        display: flex;
        align-items: flex-start;
        gap: 10px;
        margin-bottom: 16px;
    }
    .bot-avatar {
        width: 40px;
        height: 40px;
        border-radius: 50%;
        background: linear-gradient(135deg, #3B82F6, #60A5FA);
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 20px;
        flex-shrink: 0;
        box-shadow: 0 2px 8px rgba(59,130,246,0.25);
    }
    .bot-bubble {
        background: #F0F7FF;
        border-radius: 4px 18px 18px 18px;
        padding: 14px 18px;
        font-size: 14px;
        color: #1E3A5F;
        line-height: 1.6;
        max-width: 80%;
        border: 1px solid #DBEAFE;
    }
    .user-msg {
        display: flex;
        justify-content: flex-end;
        margin-bottom: 16px;
    }
    .user-bubble {
        background: linear-gradient(135deg, #2563EB, #3B82F6);
        border-radius: 18px 4px 18px 18px;
        padding: 14px 18px;
        font-size: 14px;
        color: #FFFFFF;
        line-height: 1.6;
        max-width: 80%;
        box-shadow: 0 2px 8px rgba(37,99,235,0.3);
    }

    /* ── 퀵 버튼 ── */
    .quick-buttons {
        display: flex;
        flex-wrap: wrap;
        gap: 8px;
        margin-top: 12px;
    }
    .quick-btn {
        background: #FFFFFF;
        border: 1.5px solid #3B82F6;
        border-radius: 20px;
        padding: 8px 18px;
        font-size: 13px;
        color: #2563EB;
        font-weight: 600;
        cursor: pointer;
        transition: all 0.2s ease;
    }
    .quick-btn:hover {
        background: #3B82F6;
        color: #FFFFFF;
        transform: translateY(-1px);
        box-shadow: 0 4px 12px rgba(59,130,246,0.3);
    }

    /* ── 카드 추천 카드 ── */
    .recommend-card {
        background: linear-gradient(135deg, #EFF6FF 0%, #DBEAFE 100%);
        border-radius: 16px;
        padding: 20px;
        margin: 12px 0;
        border: 1px solid #BFDBFE;
        transition: all 0.3s ease;
    }
    .recommend-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 8px 24px rgba(59,130,246,0.15);
    }
    .recommend-card .card-name {
        font-size: 17px;
        font-weight: 700;
        color: #1E40AF;
        margin-bottom: 6px;
    }
    .recommend-card .card-desc {
        font-size: 13px;
        color: #3B6EB5;
        line-height: 1.5;
    }
    .recommend-card .card-benefits {
        display: flex;
        flex-wrap: wrap;
        gap: 6px;
        margin-top: 10px;
    }
    .benefit-tag {
        background: #FFFFFF;
        border-radius: 12px;
        padding: 4px 12px;
        font-size: 12px;
        color: #2563EB;
        font-weight: 600;
        border: 1px solid #93C5FD;
    }

    /* ── 입력 영역 ── */
    .input-area {
        background: #FFFFFF;
        border-radius: 20px;
        padding: 16px 20px;
        margin: 16px 0;
        box-shadow: 0 4px 24px rgba(59,130,246,0.10);
        border: 1px solid #E8F0FE;
    }

    /* Streamlit 기본 요소 커스텀 */
    .stTextInput > div > div > input {
        border-radius: 16px !important;
        border: 2px solid #DBEAFE !important;
        padding: 12px 18px !important;
        font-size: 14px !important;
        font-family: 'Noto Sans KR', sans-serif !important;
        transition: border-color 0.2s ease !important;
    }
    .stTextInput > div > div > input:focus {
        border-color: #3B82F6 !important;
        box-shadow: 0 0 0 3px rgba(59,130,246,0.15) !important;
    }

    .stButton > button {
        background: linear-gradient(135deg, #2563EB, #3B82F6) !important;
        color: #FFFFFF !important;
        border: none !important;
        border-radius: 16px !important;
        padding: 12px 32px !important;
        font-size: 15px !important;
        font-weight: 700 !important;
        font-family: 'Noto Sans KR', sans-serif !important;
        transition: all 0.2s ease !important;
        box-shadow: 0 4px 12px rgba(37,99,235,0.3) !important;
    }
    .stButton > button:hover {
        background: linear-gradient(135deg, #1D4ED8, #2563EB) !important;
        transform: translateY(-1px) !important;
        box-shadow: 0 6px 20px rgba(37,99,235,0.4) !important;
    }

    .stSelectbox > div > div {
        border-radius: 16px !important;
        border: 2px solid #DBEAFE !important;
    }

    /* ── 푸터 ── */
    .footer {
        text-align: center;
        padding: 24px 0 16px 0;
        color: #94A3B8;
        font-size: 12px;
        line-height: 1.6;
    }
    .footer a {
        color: #3B82F6;
        text-decoration: none;
        font-weight: 600;
    }

    /* 스크롤바 커스텀 */
    .chat-wrapper::-webkit-scrollbar { width: 6px; }
    .chat-wrapper::-webkit-scrollbar-track { background: transparent; }
    .chat-wrapper::-webkit-scrollbar-thumb {
        background: #BFDBFE;
        border-radius: 3px;
    }

    /* Streamlit 기본 헤더/푸터 숨기기 */
    header[data-testid="stHeader"] { background: transparent; }
    #MainMenu { visibility: hidden; }
    footer { visibility: hidden; }
    </style>
    """,
    unsafe_allow_html=True,
)

# ──────────────────────────────────────────────
# 세션 상태 초기화
# ──────────────────────────────────────────────
if "messages" not in st.session_state:
    st.session_state.messages = [
        {
            "role": "bot",
            "content": "안녕하세요! 😊 미리은행 카드추천 챗봇입니다.\n나에게 딱 맞는 카드를 찾아드릴게요!\n아래 버튼을 눌러 시작해보세요.",
        }
    ]
if "step" not in st.session_state:
    st.session_state.step = "start"

# ──────────────────────────────────────────────
# 헤더
# ──────────────────────────────────────────────
st.markdown(
    """
    <div class="header-area">
        <div class="header-logo">M MIRIBANK</div>
        <h1 class="header-title">💳 카드추천 챗봇</h1>
        <p class="header-subtitle">은행은 멀어도 금융은 가깝게</p>
        <div class="header-badge">🤖 AI 맞춤 카드 추천 서비스</div>
    </div>
    """,
    unsafe_allow_html=True,
)

st.markdown("<div style='height: 16px'></div>", unsafe_allow_html=True)

# ──────────────────────────────────────────────
# 채팅 메시지 렌더링
# ──────────────────────────────────────────────
chat_html = '<div class="chat-wrapper">'
for msg in st.session_state.messages:
    if msg["role"] == "bot":
        text = msg["content"].replace("\n", "<br>")
        chat_html += f"""
        <div class="bot-msg">
            <div class="bot-avatar">🐻</div>
            <div class="bot-bubble">{text}</div>
        </div>
        """
    else:
        text = msg["content"].replace("\n", "<br>")
        chat_html += f"""
        <div class="user-msg">
            <div class="user-bubble">{text}</div>
        </div>
        """
chat_html += "</div>"
st.markdown(chat_html, unsafe_allow_html=True)

# ──────────────────────────────────────────────
# 퀵 버튼 (시작 단계)
# ──────────────────────────────────────────────
if st.session_state.step == "start":
    st.markdown(
        """
        <div class="card-container">
            <h3>🎯 어떤 카드를 찾고 계신가요?</h3>
        </div>
        """,
        unsafe_allow_html=True,
    )
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🛒 쇼핑·할인", use_container_width=True):
            st.session_state.messages.append({"role": "user", "content": "쇼핑·할인 카드를 찾고 있어요"})
            st.session_state.messages.append(
                {
                    "role": "bot",
                    "content": "쇼핑을 좋아하시는군요! 🛍️\n월 평균 카드 사용 금액은 어느 정도인가요?",
                }
            )
            st.session_state.step = "spending"
            st.rerun()
        if st.button("✈️ 여행·항공", use_container_width=True):
            st.session_state.messages.append({"role": "user", "content": "여행·항공 카드를 찾고 있어요"})
            st.session_state.messages.append(
                {
                    "role": "bot",
                    "content": "여행을 즐기시는군요! ✈️\n월 평균 카드 사용 금액은 어느 정도인가요?",
                }
            )
            st.session_state.step = "spending"
            st.rerun()
    with col2:
        if st.button("☕ 카페·외식", use_container_width=True):
            st.session_state.messages.append({"role": "user", "content": "카페·외식 카드를 찾고 있어요"})
            st.session_state.messages.append(
                {
                    "role": "bot",
                    "content": "맛집 탐방을 좋아하시는군요! ☕\n월 평균 카드 사용 금액은 어느 정도인가요?",
                }
            )
            st.session_state.step = "spending"
            st.rerun()
        if st.button("🚗 주유·교통", use_container_width=True):
            st.session_state.messages.append({"role": "user", "content": "주유·교통 카드를 찾고 있어요"})
            st.session_state.messages.append(
                {
                    "role": "bot",
                    "content": "운전을 자주 하시는군요! 🚗\n월 평균 카드 사용 금액은 어느 정도인가요?",
                }
            )
            st.session_state.step = "spending"
            st.rerun()

# ──────────────────────────────────────────────
# 소비 금액 선택 단계
# ──────────────────────────────────────────────
elif st.session_state.step == "spending":
    st.markdown(
        """
        <div class="card-container">
            <h3>💰 월 평균 사용 금액을 선택해주세요</h3>
        </div>
        """,
        unsafe_allow_html=True,
    )
    col1, col2 = st.columns(2)
    with col1:
        if st.button("30만원 이하", use_container_width=True):
            st.session_state.messages.append({"role": "user", "content": "월 30만원 이하 사용해요"})
            st.session_state.messages.append(
                {
                    "role": "bot",
                    "content": "알겠습니다! 분석 중이에요... 🔍\n고객님께 딱 맞는 카드를 찾았어요! 아래 추천 카드를 확인해보세요 👇",
                }
            )
            st.session_state.step = "result"
            st.rerun()
        if st.button("30~70만원", use_container_width=True):
            st.session_state.messages.append({"role": "user", "content": "월 30~70만원 사용해요"})
            st.session_state.messages.append(
                {
                    "role": "bot",
                    "content": "알겠습니다! 분석 중이에요... 🔍\n고객님께 딱 맞는 카드를 찾았어요! 아래 추천 카드를 확인해보세요 👇",
                }
            )
            st.session_state.step = "result"
            st.rerun()
    with col2:
        if st.button("70~150만원", use_container_width=True):
            st.session_state.messages.append({"role": "user", "content": "월 70~150만원 사용해요"})
            st.session_state.messages.append(
                {
                    "role": "bot",
                    "content": "알겠습니다! 분석 중이에요... 🔍\n고객님께 딱 맞는 카드를 찾았어요! 아래 추천 카드를 확인해보세요 👇",
                }
            )
            st.session_state.step = "result"
            st.rerun()
        if st.button("150만원 이상", use_container_width=True):
            st.session_state.messages.append({"role": "user", "content": "월 150만원 이상 사용해요"})
            st.session_state.messages.append(
                {
                    "role": "bot",
                    "content": "알겠습니다! 분석 중이에요... 🔍\n고객님께 딱 맞는 카드를 찾았어요! 아래 추천 카드를 확인해보세요 👇",
                }
            )
            st.session_state.step = "result"
            st.rerun()

# ──────────────────────────────────────────────
# 추천 결과 단계
# ──────────────────────────────────────────────
elif st.session_state.step == "result":
    st.markdown(
        """
        <div class="card-container">
            <h3>🏆 맞춤 추천 카드 TOP 3</h3>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # 추천 카드 1
    st.markdown(
        """
        <div class="recommend-card">
            <div class="card-name">🥇 미리 올인원 카드</div>
            <div class="card-desc">쇼핑·외식·교통 전 영역 1.5% 캐시백! 연회비 무료 혜택까지</div>
            <div class="card-benefits">
                <span class="benefit-tag">캐시백 1.5%</span>
                <span class="benefit-tag">연회비 무료</span>
                <span class="benefit-tag">전 가맹점</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # 추천 카드 2
    st.markdown(
        """
        <div class="recommend-card">
            <div class="card-name">🥈 미리 포인트 플러스</div>
            <div class="card-desc">온라인 쇼핑 3% 적립, 오프라인 1% 적립! 포인트로 현금처럼 사용</div>
            <div class="card-benefits">
                <span class="benefit-tag">온라인 3%</span>
                <span class="benefit-tag">오프라인 1%</span>
                <span class="benefit-tag">포인트 전환</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # 추천 카드 3
    st.markdown(
        """
        <div class="recommend-card">
            <div class="card-name">🥉 미리 라이프 카드</div>
            <div class="card-desc">카페·편의점·구독서비스 특화! MZ세대 맞춤 혜택</div>
            <div class="card-benefits">
                <span class="benefit-tag">카페 50%</span>
                <span class="benefit-tag">구독 할인</span>
                <span class="benefit-tag">편의점 20%</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("<div style='height: 12px'></div>", unsafe_allow_html=True)

    col1, col2 = st.columns(2)
    with col1:
        if st.button("🔄 다시 추천받기", use_container_width=True):
            st.session_state.messages = [
                {
                    "role": "bot",
                    "content": "안녕하세요! 😊 미리은행 카드추천 챗봇입니다.\n나에게 딱 맞는 카드를 찾아드릴게요!\n아래 버튼을 눌러 시작해보세요.",
                }
            ]
            st.session_state.step = "start"
            st.rerun()
    with col2:
        if st.button("💬 직접 질문하기", use_container_width=True):
            st.session_state.step = "free_chat"
            st.session_state.messages.append(
                {
                    "role": "bot",
                    "content": "궁금한 점이 있으시면 자유롭게 질문해주세요! 😊\n카드 혜택, 연회비, 신청 방법 등 무엇이든 물어보세요.",
                }
            )
            st.rerun()

# ──────────────────────────────────────────────
# 자유 채팅 단계
# ──────────────────────────────────────────────
elif st.session_state.step == "free_chat":
    user_input = st.chat_input("카드에 대해 궁금한 점을 물어보세요...")
    if user_input:
        st.session_state.messages.append({"role": "user", "content": user_input})
        # ── 여기에 실제 AI 응답 로직을 연결하세요 ──
        bot_reply = (
            f"'{user_input}'에 대해 답변드릴게요! 😊\n"
            "(이 부분에 실제 AI 응답 로직을 연결해주세요.)\n\n"
            "다른 궁금한 점이 있으시면 언제든 물어보세요!"
        )
        st.session_state.messages.append({"role": "bot", "content": bot_reply})
        st.rerun()

    if st.button("🔄 처음으로 돌아가기", use_container_width=True):
        st.session_state.messages = [
            {
                "role": "bot",
                "content": "안녕하세요! 😊 미리은행 카드추천 챗봇입니다.\n나에게 딱 맞는 카드를 찾아드릴게요!\n아래 버튼을 눌러 시작해보세요.",
            }
        ]
        st.session_state.step = "start"
        st.rerun()

# ──────────────────────────────────────────────
# 푸터
# ──────────────────────────────────────────────
st.markdown(
    """
    <div class="footer">
        <p>미리은행 카드추천 챗봇 v1.0</p>
        <p>준법감시인 심의필 제2080-0000호 (2080.00.00~2080.00.00)</p>
        <p>© 2026 MIRIBANK. All rights reserved.</p>
    </div>
    """,
    unsafe_allow_html=True,
)
