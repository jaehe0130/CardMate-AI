import uuid
import streamlit as st
from chatbot import build_chat_chain, ask_card_chatbot

st.set_page_config(
    page_title="CardMate",
    layout="centered"
)

# ---------------- 스타일 ----------------
st.markdown("""
<style>
.block-container {
    max-width: 820px;
    padding-top: 1.2rem;
}

.stApp {
    background: #f4f6f9;
}

/* 상단 */
.header-box {
    background: #ffffff;
    border-radius: 18px;
    padding: 24px;
    border: 1px solid #e5e7eb;
    margin-bottom: 20px;
}

.title {
    font-size: 1.8rem;
    font-weight: 700;
    color: #111;
}

.subtitle {
    color: #6b7280;
    margin-top: 6px;
    font-size: 0.95rem;
}

/* 카드 추천 박스 */
.result-card {
    background: white;
    border-radius: 16px;
    padding: 18px;
    margin-top: 14px;
    border: 1px solid #e5e7eb;
    box-shadow: 0 4px 10px rgba(0,0,0,0.03);
}

.card-title {
    font-size: 1.1rem;
    font-weight: 700;
    color: #111;
}

.card-sub {
    font-size: 0.9rem;
    color: #6b7280;
    margin-bottom: 8px;
}

.card-info {
    font-size: 0.9rem;
    margin-top: 6px;
}

.label {
    color: #6b7280;
    font-size: 0.8rem;
}

/* 입력창 */
.stChatInput input {
    border-radius: 999px !important;
}

/* 버튼 */
.stButton > button {
    border-radius: 999px;
    border: 1px solid #d1d5db;
    background: white;
}
</style>
""", unsafe_allow_html=True)


# ---------------- API KEY ----------------
def get_api_key():
    if "OPENAI_API_KEY" in st.secrets:
        return st.secrets["OPENAI_API_KEY"]
    raise ValueError("OPENAI_API_KEY가 secrets에 없습니다.")


@st.cache_resource
def get_chain(api_key):
    return build_chat_chain(api_key)


api_key = get_api_key()
chain = get_chain(api_key)


# ---------------- 상태 ----------------
if "messages" not in st.session_state:
    st.session_state.messages = []

if "session_id" not in st.session_state:
    st.session_state.session_id = f"user-{uuid.uuid4().hex[:8]}"


# ---------------- 헤더 ----------------
st.markdown("""
<div class="header-box">
    <div class="title">CardMate</div>
    <div class="subtitle">
        카드 혜택, 연회비, 전월실적을 비교하고 가장 적합한 카드를 추천합니다.
    </div>
</div>
""", unsafe_allow_html=True)


# ---------------- 추천 버튼 ----------------
col1, col2, col3, col4 = st.columns(4)

quick_inputs = [
    "카페 할인 좋은 카드 추천",
    "해외결제 혜택 카드",
    "연회비 낮은 체크카드",
    "편의점 할인 카드"
]

for col, q in zip([col1, col2, col3, col4], quick_inputs):
    with col:
        if st.button(q.split()[0]):
            st.session_state.messages.append({"role": "user", "content": q})


# ---------------- 채팅 출력 ----------------
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])


# ---------------- 입력 ----------------
user_input = st.chat_input("카드 조건을 입력하세요")

if user_input:
    st.session_state.messages.append({"role": "user", "content": user_input})

    with st.chat_message("user"):
        st.markdown(user_input)

    with st.chat_message("assistant"):
        with st.spinner("추천 중..."):
            try:
                response = ask_card_chatbot(
                    question=user_input,
                    chain=chain,
                    session_id=st.session_state.session_id
                )
            except Exception as e:
                response = f"오류: {e}"

        # 👉 카드 형태로 출력
        parts = response.split("###")

        for p in parts:
            if len(p.strip()) < 10:
                continue

            lines = p.strip().split("\n")

            title = lines[0]

            st.markdown(f"""
            <div class="result-card">
                <div class="card-title">{title}</div>
                <div class="card-info">{'<br>'.join(lines[1:])}</div>
            </div>
            """, unsafe_allow_html=True)

    st.session_state.messages.append({"role": "assistant", "content": response})
