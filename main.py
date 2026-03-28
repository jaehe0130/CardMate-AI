import streamlit as st
from prompts import chat

# Streamlit 기본 설정
st.title("카드 추천 챗봇")
st.write("당신에게 가장 적합한 카드를 추천해 드립니다.")

# 사용자 질문 입력
user_question = st.text_input("질문을 입력하세요:")

# 세션 ID 설정
config = {"configurable": {"session_id": "card_expert_session"}}

if st.button("질문하기"):
    if user_question:
        response = chat(user_question, config)
        st.write(response)
    else:
        st.warning("질문을 입력해 주세요.")
