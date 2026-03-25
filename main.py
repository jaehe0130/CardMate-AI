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
.chat-title {
    font-size: 2rem;
    font-weight: 700;
    margin-bottom: 0.3rem;
}
.chat-subtitle {
    color: #666;
    margin-bottom: 1.2rem;
}
.quick-guide {
    padding: 14px 16px;
    border-radius: 12px;
    background: #f6f7f9;
    border: 1px solid #e8eaef;
    margin-bottom: 1rem;
}
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="chat-title">CardMate AI</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="chat-subtitle">카드 혜택, 연회비, 전월실적, 추천 질문을 편하게 물어보세요.</div>',
    unsafe_allow_html=True
)

st.markdown("""
<div class="quick-guide">
예시 질문
<br>- 카페 할인 좋은 체크카드 추천해줘
<br>- 해외결제 수수료 혜택 있는 카드 알려줘
<br>- 연회비 낮고 전월실적 부담 적은 카드 추천해줘
<br>- 신한카드 SOL트래블 체크 연회비 얼마야?
</div>
""", unsafe_allow_html=True)

if "messages" not in st.session_state:
    st.session_state.messages = [
        {
            "role": "assistant",
            "content": "안녕하세요. 카드 혜택 안내와 추천을 도와드릴게요. 궁금한 점을 입력해주세요."
        }
    ]

if "session_id" not in st.session_state:
    st.session_state.session_id = "streamlit_user_1"

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
