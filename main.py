import os
import streamlit as st

from chatbot import init_session_state, process_user_input
from utils import (
    render_sidebar,
    render_chat_messages,
    render_card_list,
    render_hero_section,
    render_quick_actions,
    render_preference_summary,
    render_service_notice
)

st.set_page_config(
    page_title="CardMate AI",
    page_icon="💳",
    layout="wide"
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

html, body, [class*="css"] {
    font-family: 'Inter', sans-serif;
}

.stApp {
    background: linear-gradient(180deg, #F4F7FB 0%, #EDF2F8 100%);
    color: #0F172A;
}

.block-container {
    max-width: 1180px;
    padding-top: 1.2rem;
    padding-bottom: 2.4rem;
}

section[data-testid="stSidebar"] {
    background: #0F172A;
    border-right: 1px solid rgba(255,255,255,0.06);
}

section[data-testid="stSidebar"] * {
    color: #F8FAFC !important;
}

.hero-wrap {
    background:
        radial-gradient(circle at top right, rgba(255,255,255,0.10), transparent 28%),
        linear-gradient(135deg, #0F172A 0%, #172554 45%, #1D4ED8 100%);
    border-radius: 28px;
    padding: 34px 34px 30px 34px;
    color: white;
    box-shadow: 0 18px 50px rgba(15, 23, 42, 0.22);
    margin-bottom: 18px;
}

.hero-badge {
    display: inline-block;
    padding: 7px 12px;
    border-radius: 999px;
    background: rgba(255,255,255,0.12);
    border: 1px solid rgba(255,255,255,0.14);
    font-size: 0.82rem;
    font-weight: 600;
    margin-bottom: 14px;
}

.hero-title {
    font-size: 2.25rem;
    font-weight: 800;
    line-height: 1.2;
    margin-bottom: 0.7rem;
    letter-spacing: -0.02em;
}

.hero-desc {
    font-size: 1rem;
    color: rgba(255,255,255,0.88);
    line-height: 1.7;
    margin-bottom: 1rem;
}

.hero-chip {
    display: inline-block;
    padding: 9px 13px;
    border-radius: 999px;
    background: rgba(255,255,255,0.11);
    border: 1px solid rgba(255,255,255,0.10);
    font-size: 0.87rem;
    margin-right: 8px;
    margin-top: 8px;
}

.surface-card {
    background: rgba(255,255,255,0.88);
    backdrop-filter: blur(8px);
    border: 1px solid rgba(226,232,240,0.9);
    border-radius: 24px;
    padding: 18px 18px 12px 18px;
    box-shadow: 0 10px 30px rgba(15, 23, 42, 0.06);
    margin-bottom: 16px;
}

.section-title {
    font-size: 1.08rem;
    font-weight: 800;
    color: #0F172A;
    margin-bottom: 12px;
    letter-spacing: -0.01em;
}

.subtle-text {
    color: #475569;
    font-size: 0.94rem;
}

.pref-wrap {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
    margin-top: 6px;
}

.pref-chip {
    display: inline-block;
    padding: 8px 12px;
    border-radius: 999px;
    background: #FFFFFF;
    border: 1px solid #DCE5F0;
    color: #0F172A;
    font-size: 0.86rem;
    font-weight: 600;
}

.notice-box {
    background: linear-gradient(180deg, #FFFFFF 0%, #F8FBFF 100%);
    border: 1px solid #DCE8F6;
    border-radius: 18px;
    padding: 14px 16px;
    margin-bottom: 14px;
}

.notice-title {
    font-weight: 700;
    color: #0F172A;
    margin-bottom: 4px;
}

.notice-desc {
    color: #475569;
    font-size: 0.92rem;
    line-height: 1.6;
}

.quick-btn-wrap {
    margin-top: 6px;
}

div[data-testid="stChatMessage"] {
    background: transparent;
}

div[data-testid="stChatMessageContent"] {
    border-radius: 18px;
    padding: 0.95rem 1rem;
}

.card-shell {
    background: linear-gradient(180deg, #FFFFFF 0%, #F9FBFD 100%);
    border: 1px solid #E2E8F0;
    border-radius: 24px;
    padding: 16px;
    box-shadow: 0 10px 28px rgba(15, 23, 42, 0.06);
    min-height: 100%;
}

.card-top-badge {
    display: inline-block;
    padding: 6px 10px;
    border-radius: 999px;
    background: #EAF2FF;
    color: #1D4ED8;
    font-size: 0.77rem;
    font-weight: 700;
    margin-bottom: 10px;
}

.card-title {
    font-size: 1.18rem;
    font-weight: 800;
    color: #0F172A;
    margin-top: 8px;
    margin-bottom: 8px;
    letter-spacing: -0.01em;
}

.card-meta {
    color: #475569;
    font-size: 0.92rem;
    margin-bottom: 12px;
    line-height: 1.7;
}

.card-benefit {
    background: #F8FAFC;
    border: 1px solid #E2E8F0;
    border-radius: 16px;
    padding: 12px;
    color: #334155;
    font-size: 0.92rem;
    line-height: 1.6;
    min-height: 96px;
}

.card-link a {
    color: #1D4ED8 !important;
    text-decoration: none;
    font-weight: 700;
}

.result-head {
    margin-top: 6px;
    margin-bottom: 12px;
}

.stButton > button {
    border-radius: 14px !important;
    border: 1px solid #D6E0EC !important;
    background: #FFFFFF !important;
    color: #0F172A !important;
    font-weight: 700 !important;
    padding: 0.75rem 1rem !important;
}

.stButton > button:hover {
    border-color: #BFD2EA !important;
    background: #F8FBFF !important;
}

.stChatInputContainer {
    background: transparent !important;
}

hr {
    border-color: #E2E8F0 !important;
}
</style>
""", unsafe_allow_html=True)

api_key = st.secrets.get("OPENAI_API_KEY") if hasattr(st, "secrets") else None
if not api_key:
    api_key = os.getenv("OPENAI_API_KEY")

sidebar_filters = render_sidebar()
init_session_state()

render_hero_section()
render_service_notice()

quick_prompt = render_quick_actions()
user_input = quick_prompt if quick_prompt else None

st.markdown('<div class="surface-card">', unsafe_allow_html=True)
render_preference_summary(st.session_state.user_prefs, sidebar_filters)
st.markdown('</div>', unsafe_allow_html=True)

st.markdown('<div class="surface-card">', unsafe_allow_html=True)
st.markdown('<div class="section-title">AI 카드 추천 상담</div>', unsafe_allow_html=True)
render_chat_messages(st.session_state.messages)
st.markdown('</div>', unsafe_allow_html=True)

chat_input = st.chat_input("예: 편의점, 통신비, 공과금 할인 좋고 실적 부담 적은 신용카드 추천해줘")
if chat_input:
    user_input = chat_input

if user_input:
    st.session_state.messages.append({
        "role": "user",
        "content": user_input
    })

    result = process_user_input(
        user_input=user_input,
        sidebar_filters=sidebar_filters,
        api_key=api_key
    )

    st.session_state.user_prefs = result["preferences"]
    st.session_state.last_cards = result["cards"]

    st.session_state.messages.append({
        "role": "assistant",
        "content": result["message"]
    })

    st.rerun()

if st.session_state.last_cards:
    st.markdown('<div class="result-head">', unsafe_allow_html=True)
    st.markdown('<div class="section-title">추천 카드</div>', unsafe_allow_html=True)
    st.markdown('<div class="subtle-text">현재 대화 내용과 선택 조건을 바탕으로 추천된 카드입니다.</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)
    render_card_list(st.session_state.last_cards)
