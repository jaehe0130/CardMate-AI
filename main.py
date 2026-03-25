import uuid
import streamlit as st

from chatbot import build_chat_chain, ask_card_chatbot

st.set_page_config(
    page_title="CardMate AI",
    page_icon="💳",
    layout="centered"
)

st.markdown("""
<style>
.block-container {
    max-width: 760px;
    padding-top: 1.2rem;
    padding-bottom: 2rem;
}
.stApp {
    background: #f6f7fb;
}
.top-wrap {
    background: linear-gradient(135deg, #111111 0%, #2c2f36 100%);
    border-radius: 22px;
    padding: 24px 22px;
    margin-bottom: 18px;
    color: white;
    box-shadow: 0 10px 30px rgba(0,0,0,0.12);
}
.top-title {
    font-size: 2rem;
    font-weight: 800;
    margin-bottom: 0.3rem;
}
.top-subtitle {
    font-size: 0.98rem;
    color: rgba(255,255,255,0.82);
    line-height: 1.5;
}
.quick-card {
    background: white;
    border: 1px solid #e9edf2;
    border-radius: 18px;
    padding: 16px;
    margin-bottom: 14px;
    box-shadow: 0 4px 14px rgba(0,0,0,0.04);
}
.quick-title {
    font-size: 1rem;
    font-weight: 700;
    margin-bottom: 10px;
    color: #111;
}
[data-testid="stChatMessage"] {
    background: white;
    border: 1px solid #eceff3;
    border-radius: 18px;
    padding: 6px 4px;
    margin-bottom: 10px;
    box-shadow: 0 4px 14px rgba(0,0,0,0.03);
}
.stButton > button {
    border-radius: 999px;
    border: 1px solid #e5e7eb;
    background: white;
}
</style>
""", unsafe_allow_html=True)


def get_openai_api_key() -> str:
    # Streamlit Cloud secrets 우선
    if "OPENAI_API_KEY" in st.secrets:
        return st.secrets["OPENAI_API_KEY"]
    raise ValueError("Streamlit secrets에 OPENAI_API_KEY를 설정해주세요.")


@st.cache_resource
def get_cached_chain(api_key: str):
    return build_chat_chain(api_key)


api_key = get_openai_api_key()
chain = get_cached_chain(api_key)

if "messages" not in st.session_state:
    st.session_state.messages = [
        {
            "role": "assistant",
            "content": "안녕하세요. 카드 추천과 혜택 안내를 도와드릴게요."
        }
    ]

if "session_id" not in st.session_state:
    st.session_state.session_id = f"cardmate-{uuid.uuid4().hex[:10]}"

if "pending_prompt" not in st.session_state:
    st.session_state.pending_prompt = None


def reset_chat():
    st.session_state.messages = [
        {
            "role": "assistant",
            "content": "새 대화를 시작했어요. 원하는 카드 조건을 말씀해주세요."
        }
    ]
    st.session_state.session_id = f"cardmate-{uuid.uuid4().hex[:10]}"
    st.session_state.pending_prompt = None


with st.sidebar:
    st.markdown("### CardMate AI")
    st.caption("카드 추천 챗봇")
    if st.button("새 대화", use_container_width=True):
        reset_chat()
        st.rerun()

st.markdown("""
<div class="top-wrap">
    <div class="top-title">CardMate AI</div>
    <div class="top-subtitle">
        Streamlit Secrets 기반으로 안전하게 키를 읽고,
        시맨틱 검색으로 카드 추천을 도와드려요.
    </div>
</div>
""", unsafe_allow_html=True)

st.markdown("""
<div class="quick-card">
    <div class="quick-title">빠르게 시작하기</div>
</div>
""", unsafe_allow_html=True)

chip_cols = st.columns(4)
chip_prompts = [
    "카페 할인 좋은 카드 3개 추천해줘",
    "해외결제 혜택 좋은 카드 추천해줘",
    "연회비 낮은 체크카드 추천해줘",
    "편의점 혜택 좋은 카드 추천해줘",
]

for col, prompt in zip(chip_cols, chip_prompts):
    with col:
        if st.button(prompt.split(" ")[0], use_container_width=True):
            st.session_state.pending_prompt = prompt

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

user_input = st.chat_input("예: 연회비 낮고 카페 할인 좋은 체크카드 추천해줘")
final_input = user_input or st.session_state.pending_prompt

if final_input:
    if st.session_state.pending_prompt:
        st.session_state.pending_prompt = None

    st.session_state.messages.append({"role": "user", "content": final_input})

    with st.chat_message("user"):
        st.markdown(final_input)

    with st.chat_message("assistant"):
        with st.spinner("카드 정보를 찾고 있어요..."):
            try:
                response = ask_card_chatbot(
                    question=final_input,
                    chain=chain,
                    session_id=st.session_state.session_id
                )
            except Exception as e:
                response = f"오류가 발생했습니다: {e}"

            st.markdown(response)

    st.session_state.messages.append({"role": "assistant", "content": response})
