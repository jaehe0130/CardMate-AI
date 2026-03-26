import uuid
import streamlit as st
from recommender import ask_card_bot

st.set_page_config(
    page_title="CardMate AI",
    page_icon="💳",
    layout="wide"
)

if "session_id" not in st.session_state:
    st.session_state.session_id = f"user_{uuid.uuid4().hex[:8]}"

if "messages" not in st.session_state:
    st.session_state.messages = []

st.markdown("""
<style>
.main-title {
    font-size: 2rem;
    font-weight: 800;
    color: #1f2937;
    margin-bottom: 0.2rem;
}
.sub-title {
    color: #6b7280;
    margin-bottom: 1.2rem;
}
.user-box {
    background: #eaf2ff;
    padding: 14px 16px;
    border-radius: 14px;
    margin-bottom: 10px;
}
.bot-box {
    background: #ffffff;
    border: 1px solid #e5e7eb;
    padding: 16px 18px;
    border-radius: 14px;
    margin-bottom: 12px;
}
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="main-title">💳 CardMate AI</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-title">조건에 맞는 카드 혜택을 찾아 추천해주는 챗봇</div>', unsafe_allow_html=True)

with st.sidebar:
    st.header("빠른 질문")
    samples = [
        "나 18살 학생인데, 편의점이랑 교통비 할인 많이 되는 체크카드 추천해줘",
        "배달이랑 외식 혜택 좋은 신용카드 추천해줘",
        "해외여행 마일리지 적립 좋은 신용카드 추천해줘",
        "마트 장보기 할인 좋은 카드 추천해줘",
        "인기 많은 체크카드 추천해줘",
    ]
    for q in samples:
        if st.button(q, use_container_width=True):
            st.session_state["quick_question"] = q

for msg in st.session_state.messages:
    box_class = "user-box" if msg["role"] == "user" else "bot-box"
    st.markdown(f'<div class="{box_class}">{msg["content"]}</div>', unsafe_allow_html=True)

user_input = st.chat_input("질문을 입력하세요")

if "quick_question" in st.session_state:
    user_input = st.session_state["quick_question"]
    del st.session_state["quick_question"]

if user_input:
    st.session_state.messages.append({"role": "user", "content": user_input})
    st.markdown(f'<div class="user-box">{user_input}</div>', unsafe_allow_html=True)

    with st.spinner("카드를 추천하는 중입니다..."):
        try:
            answer = ask_card_bot(
                question=user_input,
                session_id=st.session_state.session_id
            )
        except Exception as e:
            answer = f"오류가 발생했습니다: {e}"

    st.session_state.messages.append({"role": "assistant", "content": answer})
    st.markdown(f'<div class="bot-box">{answer}</div>', unsafe_allow_html=True)
