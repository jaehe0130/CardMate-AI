import streamlit as st

st.set_page_config(page_title="CardMate", layout="wide")

# -------------------------------
# 🎨 토스 스타일 CSS
# -------------------------------
st.markdown("""
<style>
body {
    background-color: #F5F7FA;
}

.block-container {
    padding-top: 2rem;
}

/* 카드 박스 */
.card-box {
    background-color: white;
    padding: 20px;
    border-radius: 20px;
    margin-bottom: 15px;
    box-shadow: 0px 4px 12px rgba(0,0,0,0.05);
}

/* 제목 */
.title {
    font-size: 28px;
    font-weight: 700;
}

/* 서브텍스트 */
.subtitle {
    color: #6B7280;
    font-size: 14px;
}

/* 버튼 */
.stButton>button {
    background-color: #4A90E2;
    color: white;
    border-radius: 10px;
    height: 45px;
    font-weight: 600;
}
</style>
""", unsafe_allow_html=True)

# -------------------------------
# 상태
# -------------------------------
if "messages" not in st.session_state:
    st.session_state.messages = []

if "persona" not in st.session_state:
    st.session_state.persona = {}

# -------------------------------
# Sidebar
# -------------------------------
st.sidebar.title("👤 사용자 설정")

name = st.sidebar.text_input("이름", "취준생")
cafe = st.sidebar.slider("카페 소비", 0, 500000, 100000)
travel = st.sidebar.slider("여행 소비", 0, 500000, 0)

if st.sidebar.button("💾 저장"):
    st.session_state.persona = {
        "name": name,
        "카페": cafe,
        "여행": travel
    }
    st.sidebar.success("저장 완료")

# -------------------------------
# 더미 추천
# -------------------------------
def recommend(persona):
    if persona.get("여행", 0) > 100000:
        return [
            {"name": "대한항공 마일리지 카드", "desc": "해외 여행 최적화", "img": "https://via.placeholder.com/120"},
            {"name": "신한 Air 카드", "desc": "항공 적립 특화", "img": "https://via.placeholder.com/120"},
        ]
    else:
        return [
            {"name": "삼성 taptap O", "desc": "카페 할인 최적", "img": "https://via.placeholder.com/120"},
            {"name": "신한 Mr.Life", "desc": "생활 할인 카드", "img": "https://via.placeholder.com/120"},
        ]

# -------------------------------
# 카드 UI
# -------------------------------
def show_card(card):
    st.markdown(f"""
    <div class="card-box">
        <div style="display:flex; align-items:center;">
            <img src="{card['img']}" width="80" style="margin-right:15px;">
            <div>
                <div style="font-size:18px; font-weight:600;">💳 {card['name']}</div>
                <div class="subtitle">{card['desc']}</div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

# -------------------------------
# 메인 화면
# -------------------------------
st.markdown('<div class="title">💳 CardMate</div>', unsafe_allow_html=True)
st.markdown('<div class="subtitle">나에게 딱 맞는 카드 추천</div>', unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# -------------------------------
# 채팅 출력
# -------------------------------
for msg in st.session_state.messages:
    st.chat_message(msg["role"]).write(msg["content"])

# -------------------------------
# 입력
# -------------------------------
user_input = st.chat_input("소비 패턴을 말해보세요")

if user_input:

    # 유저 메시지
    st.session_state.messages.append({"role": "user", "content": user_input})
    st.chat_message("user").write(user_input)

    persona = st.session_state.persona

    if not persona:
        st.warning("먼저 좌측에서 사용자 정보를 입력하세요.")
        st.stop()

    # 추천
    cards = recommend(persona)

    # 응답
    response = f"""
{persona['name']}님 소비 패턴을 분석해봤어요 😎

👉 카페: {persona['카페']}
👉 여행: {persona['여행']}

이 카드가 잘 맞아요 👇
"""

    st.session_state.messages.append({"role": "assistant", "content": response})

    # 스트리밍 느낌
    with st.chat_message("assistant"):
        for word in response.split():
            st.write(word + " ")

    # 카드 출력
    for c in cards:
        show_card(c)
