# app.py
# =========================================================
# [이 파일의 역할]
# - Streamlit UI
# - 질문 입력
# - moderation 통과 시 카드 추천 결과 + 이미지 카드 UI 출력
# =========================================================

import uuid
import streamlit as st

from prompts import ask_card_bot
from recommender import get_recommendation_cards

st.set_page_config(
    page_title="CardMate AI",
    page_icon="💳",
    layout="wide"
)

if "session_id" not in st.session_state:
    st.session_state.session_id = f"user_{uuid.uuid4().hex[:8]}"

if "messages" not in st.session_state:
    st.session_state.messages = []

if "latest_cards" not in st.session_state:
    st.session_state.latest_cards = []

st.markdown("""
<style>
.block-container {
    padding-top: 2rem;
    max-width: 1200px;
}
.main-title {
    font-size: 2rem;
    font-weight: 800;
    color: #111827;
}
.sub-title {
    color: #6b7280;
    margin-bottom: 1.2rem;
}
.card-box {
    background: #ffffff;
    border: 1px solid #e5e7eb;
    border-radius: 20px;
    padding: 16px;
    box-shadow: 0 8px 20px rgba(0,0,0,0.05);
    min-height: 430px;
}
.badge {
    display: inline-block;
    background: #4f7cff;
    color: white;
    padding: 5px 10px;
    border-radius: 999px;
    font-size: 0.8rem;
    font-weight: 700;
    margin-bottom: 10px;
}
.meta {
    background: #f8fafc;
    border-radius: 12px;
    padding: 10px 12px;
    margin: 10px 0;
    font-size: 0.92rem;
}
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="main-title">💳 CardMate AI</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-title">조건에 맞는 카드 혜택과 이미지를 함께 비교해보세요.</div>', unsafe_allow_html=True)

with st.sidebar:
    st.header("빠른 질문")
    samples = [
        "인기있는 카드 3개 추천해줘",
        "편의점이랑 교통비 할인 많이 되는 체크카드 추천해줘",
        "배달이랑 외식 혜택 좋은 신용카드 추천해줘",
        "해외여행 마일리지 적립 좋은 신용카드 추천해줘",
    ]
    for q in samples:
        if st.button(q, use_container_width=True):
            st.session_state["quick_question"] = q

user_input = st.chat_input("예: 편의점이랑 교통비 할인 많이 되는 체크카드 추천해줘")

if "quick_question" in st.session_state:
    user_input = st.session_state["quick_question"]
    del st.session_state["quick_question"]

if user_input:
    with st.spinner("카드를 분석하는 중입니다..."):
        result = ask_card_bot(
            question=user_input,
            session_id=st.session_state.session_id
        )

        answer = result["answer"]

        # moderation 통과한 경우에만 카드 이미지 UI 생성
        if result["ok"]:
            cards = get_recommendation_cards(user_input)
        else:
            cards = []

    st.session_state.messages.append({"role": "user", "content": user_input})
    st.session_state.messages.append({"role": "assistant", "content": answer})
    st.session_state.latest_cards = cards

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

if st.session_state.latest_cards:
    st.markdown("## 추천 카드 TOP 3")
    cols = st.columns(3)

    for idx, card in enumerate(st.session_state.latest_cards[:3]):
        with cols[idx]:
            st.markdown('<div class="card-box">', unsafe_allow_html=True)
            st.markdown(f'<div class="badge">TOP {idx+1}</div>', unsafe_allow_html=True)

            if card["image_url"]:
                st.image(card["image_url"], use_container_width=True)
            else:
                st.info("이미지 URL 없음")

            st.markdown(f"### {card['card_name']}")
            st.markdown(
                f"""
                <div class="meta">
                <b>연회비</b>: {card['annual_fee']}<br>
                <b>전월실적</b>: {card['performance']}
                </div>
                """,
                unsafe_allow_html=True
            )
            st.write(card["benefit_summary"])
            st.markdown("</div>", unsafe_allow_html=True)
