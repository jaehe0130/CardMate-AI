import streamlit as st

st.set_page_config(page_title="CardMate Chat")

# -------------------------------
# 상태 초기화
# -------------------------------
if "messages" not in st.session_state:
    st.session_state.messages = []

if "user_profile" not in st.session_state:
    st.session_state.user_profile = {
        "카페": 0,
        "배달": 0,
        "쇼핑": 0,
        "여행": 0
    }


# -------------------------------
# 입력 → 프로필 업데이트
# -------------------------------
def update_profile(user_input):
    if "카페" in user_input:
        st.session_state.user_profile["카페"] += 1
    if "배달" in user_input:
        st.session_state.user_profile["배달"] += 1
    if "여행" in user_input:
        st.session_state.user_profile["여행"] += 1


# -------------------------------
# 추천 로직 (더미)
# -------------------------------
def recommend(profile):
    if profile["여행"] > 0:
        return ["마일리지 카드", "해외 특화 카드"]
    elif profile["카페"] > 0:
        return ["카페 할인 카드"]
    else:
        return ["기본 카드"]


# -------------------------------
# UI
# -------------------------------
st.title("💳 CardMate AI 챗봇")

# 기존 대화 출력
for msg in st.session_state.messages:
    st.chat_message(msg["role"]).write(msg["content"])

# 사용자 입력
user_input = st.chat_input("소비 패턴을 말해보세요")

if user_input:

    # 1. 메시지 저장
    st.session_state.messages.append({
        "role": "user",
        "content": user_input
    })
    st.chat_message("user").write(user_input)

    # 2. 프로필 업데이트
    update_profile(user_input)

    # 3. 추천
    cards = recommend(st.session_state.user_profile)

    # 4. 응답 생성 (챗봇 스타일)
    response = f"""
지금까지 이야기 들어보면 👇

👉 카페: {st.session_state.user_profile['카페']}
👉 여행: {st.session_state.user_profile['여행']}

그래서 이런 카드가 좋아 👇
"""

    # 5. 응답 저장
    st.session_state.messages.append({
        "role": "assistant",
        "content": response
    })

    # 6. 출력
    st.chat_message("assistant").write(response)

    # 7. 카드 표시
    for c in cards:
        st.write(f"💳 {c}")
