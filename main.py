import os
import streamlit as st

from chatbot import init_session_state, process_user_input
from utils import render_sidebar, render_chat_messages, render_card_list

st.set_page_config(
    page_title="CardMate AI",
    page_icon="💳",
    layout="wide"
)

st.markdown("""
<style>
.block-container {
    max-width: 1100px;
    padding-top: 1.5rem;
    padding-bottom: 2rem;
}
.main-title {
    font-size: 2rem;
    font-weight: 800;
    margin-bottom: 0.2rem;
}
.sub-title {
    color: #666;
    margin-bottom: 1rem;
}
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="main-title">💳 CardMate AI</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-title">생활패턴에 맞는 카드를 대화형으로 추천해드려요.</div>', unsafe_allow_html=True)

# Streamlit Cloud secrets 우선, 없으면 환경변수
api_key = st.secrets.get("OPENAI_API_KEY") or os.getenv("OPENAI_API_KEY")

sidebar_filters = render_sidebar()
init_session_state()

render_chat_messages(st.session_state.messages)

user_input = st.chat_input("예: 편의점, 통신비, 공과금 할인 좋고 실적 부담 적은 신용카드 추천해줘")

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
    st.markdown("---")
    st.subheader("추천 카드")
    render_card_list(st.session_state.last_cards)
