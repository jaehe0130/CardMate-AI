import streamlit as st
from chatbot import ask_card_chatbot

st.set_page_config(
    page_title="CardMate AI",
    page_icon="💳",
    layout="centered"
)

st.markdown("""
<style>
.block-container {
    max-width: 760px;
    padding-top: 2rem;
    padding-bottom: 2rem;
}
.title {
    font-size: 2rem;
    font-weight: 700;
    margin-bottom: 0.25rem;
}
.subtitle {
    color: #666;
    margin-bottom: 1rem;
}
.guide-box {
    background: #f7f8fa;
    border: 1px solid #e9edf2;
    border-radius: 12px;
    padding: 14px 16px;
    margin-bottom: 1rem;
}
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="title">CardMate AI</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="subtitle">카드 추천, 혜택, 연회비, 실적 조건을 물어보세요.</div>',
    unsafe_allow_html=True
)

st.markdown("""
<div class="guide-box">
예시 질문
<br>- 편의점 혜택 좋은 카드 3개 추천해줘
<br>- 연회비 낮고 카페 할인 좋은 체크카드 추천해줘
<br>- 방금 추천한 카드 중 전월실적이 가장 낮은 건 뭐야?
<br>- 특정 카드 연회비 얼마야?
</div>
""", unsafe_allow_html=True)

if "messages" not in st.session_state:
    st.session_state.messages = [
        {
            "role": "assistant",
            "content": "안녕하세요. 카드 추천과 혜택 안내를 도와드릴게요."
        }
    ]

if "session_id" not in st.session_state:
    st.session_state.session_id = "streamlit_cardmate_user"

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

user_input = st.chat_input("카드 관련 질문을 입력하세요")

if user_input:
    st.session_state.messages.append({"role": "user", "content": user_input})

    with st.chat_message("user"):
        st.markdown(user_input)

    with st.chat_message("assistant"):
        with st.spinner("답변 생성 중..."):
            response = ask_card_chatbot(
                question=user_input,
                session_id=st.session_state.session_id
            )
            st.markdown(response)

    st.session_state.messages.append({"role": "assistant", "content": response})
