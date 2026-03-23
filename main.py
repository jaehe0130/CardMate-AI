import streamlit as st
import json

st.set_page_config(page_title="CardMate AI", layout="wide")

# -------------------------------
# 상태 초기화
# -------------------------------
if "messages" not in st.session_state:
    st.session_state.messages = []

if "persona" not in st.session_state:
    st.session_state.persona = {}

# -------------------------------
# Sidebar (페르소나 입력🔥)
# -------------------------------
st.sidebar.title("👤 페르소나 설정")

name = st.sidebar.text_input("이름", "취준생")

cafe = st.sidebar.slider("카페 소비", 0, 500000, 100000)
delivery = st.sidebar.slider("배달 소비", 0, 500000, 50000)
shopping = st.sidebar.slider("쇼핑 소비", 0, 500000, 100000)
travel = st.sidebar.slider("여행 소비", 0, 500000, 0)

priority = st.sidebar.selectbox("우선 기준", ["할인", "적립"])

# -------------------------------
# JSON 저장
# -------------------------------
if st.sidebar.button("💾 페르소나 저장"):

    persona = {
        "name": name,
        "spending": {
            "카페": cafe,
            "배달": delivery,
            "쇼핑": shopping,
            "여행": travel
        },
        "priority": priority
    }

    with open("persona.json", "w", encoding="utf-8") as f:
        json.dump(persona, f, ensure_ascii=False, indent=4)

    st.session_state.persona = persona
    st.success("페르소나 저장 완료!")

# -------------------------------
# 더미 추천 (나중에 교체)
# -------------------------------
def recommend(persona, user_input):

    # 간단 로직
    if persona["spending"]["여행"] > 100000:
        return [
            {"name": "마일리지 카드", "image": "https://via.placeholder.com/120"},
            {"name": "해외 특화 카드", "image": "https://via.placeholder.com/120"},
        ]
    else:
        return [
            {"name": "카페 할인 카드", "image": "https://via.placeholder.com/120"},
            {"name": "생활 할인 카드", "image": "https://via.placeholder.com/120"},
        ]

# -------------------------------
# 메인 UI
# -------------------------------
st.title("💳 CardMate AI 챗봇")

# 기존 대화 출력
for msg in st.session_state.messages:
    st.chat_message(msg["role"]).write(msg["content"])

# 사용자 입력
user_input = st.chat_input("소비 패턴을 말해보세요")

if user_input:

    # 유저 메시지 저장
    st.session_state.messages.append({
        "role": "user",
        "content": user_input
    })
    st.chat_message("user").write(user_input)

    # 페르소나 불러오기
    persona = st.session_state.persona

    if not persona:
        st.warning("먼저 페르소나를 저장하세요!")
        st.stop()

    # 추천 실행
    cards = recommend(persona, user_input)

    # 응답 생성
    response = f"""
{persona['name']}님의 소비 패턴을 반영해서 추천해볼게 😎

👉 카페: {persona['spending']['카페']}
👉 여행: {persona['spending']['여행']}

이런 카드가 좋아 👇
"""

    st.session_state.messages.append({
        "role": "assistant",
        "content": response
    })

    st.chat_message("assistant").write(response)

    # 카드 출력
    for card in cards:
        col1, col2 = st.columns([1, 4])

        with col1:
            st.image(card["image"], width=100)

        with col2:
            st.write(f"💳 {card['name']}")
            st.divider()
