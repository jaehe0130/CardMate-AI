import uuid
import streamlit as st
from recommender import ask_card_bot, get_recommendation_cards

st.set_page_config(
    page_title="CardMate AI",
    page_icon="💳",
    layout="wide"
)

# 세션 초기화
if "session_id" not in st.session_state:
    st.session_state.session_id = f"user_{uuid.uuid4().hex[:8]}"

if "messages" not in st.session_state:
    st.session_state.messages = []

if "latest_cards" not in st.session_state:
    st.session_state.latest_cards = []

# -----------------------------
# CSS
# -----------------------------
st.markdown("""
<style>
.block-container {
    padding-top: 2rem;
    padding-bottom: 2rem;
    max-width: 1200px;
}

.main-title {
    font-size: 2.2rem;
    font-weight: 800;
    color: #111827;
    margin-bottom: 0.25rem;
}

.sub-title {
    color: #6b7280;
    font-size: 1rem;
    margin-bottom: 1.5rem;
}

.user-box {
    background: #EAF2FF;
    color: #111827;
    padding: 14px 16px;
    border-radius: 16px;
    margin-bottom: 10px;
    border: 1px solid #D7E5FF;
}

.bot-box {
    background: #FFFFFF;
    color: #111827;
    padding: 16px 18px;
    border-radius: 16px;
    margin-bottom: 14px;
    border: 1px solid #E5E7EB;
    box-shadow: 0 4px 14px rgba(0,0,0,0.04);
}

.section-title {
    font-size: 1.25rem;
    font-weight: 700;
    color: #111827;
    margin-top: 1.5rem;
    margin-bottom: 0.8rem;
}

.card-wrap {
    background: #FFFFFF;
    border: 1px solid #E5E7EB;
    border-radius: 22px;
    padding: 16px;
    box-shadow: 0 8px 24px rgba(15,23,42,0.06);
    min-height: 460px;
}

.card-rank {
    display: inline-block;
    font-size: 0.8rem;
    font-weight: 700;
    color: white;
    background: #4F7CFF;
    padding: 6px 10px;
    border-radius: 999px;
    margin-bottom: 12px;
}

.card-name {
    font-size: 1.15rem;
    font-weight: 800;
    color: #111827;
    margin-top: 10px;
    margin-bottom: 10px;
    line-height: 1.35;
    min-height: 48px;
}

.card-meta {
    font-size: 0.92rem;
    color: #374151;
    background: #F8FAFC;
    border-radius: 12px;
    padding: 10px 12px;
    margin-bottom: 12px;
    line-height: 1.6;
}

.card-benefit-title {
    font-size: 0.95rem;
    font-weight: 700;
    color: #111827;
    margin-bottom: 6px;
}

.card-benefit {
    font-size: 0.92rem;
    color: #4B5563;
    line-height: 1.6;
}

.empty-image {
    width: 100%;
    height: 220px;
    border-radius: 18px;
    background: linear-gradient(135deg, #EEF4FF, #F8FAFC);
    display: flex;
    align-items: center;
    justify-content: center;
    color: #6B7280;
    font-weight: 700;
    border: 1px dashed #CBD5E1;
}
</style>
""", unsafe_allow_html=True)

# -----------------------------
# 헤더
# -----------------------------
st.markdown('<div class="main-title">💳 CardMate AI</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="sub-title">조건에 맞는 카드를 찾고, 핵심 혜택까지 한눈에 비교해보세요.</div>',
    unsafe_allow_html=True
)

# -----------------------------
# 사이드바
# -----------------------------
with st.sidebar:
    st.header("빠른 질문")
    sample_questions = [
        "편의점이랑 교통비 할인 많이 되는 체크카드 추천해줘",
        "배달이랑 외식 혜택 좋은 신용카드 추천해줘",
        "해외여행 마일리지 적립 좋은 신용카드 추천해줘",
        "마트 장보기랑 자녀 학원비 할인되는 신용카드 추천해줘",
        "인기 많은 체크카드 추천해줘",
    ]
    for q in sample_questions:
        if st.button(q, use_container_width=True):
            st.session_state["quick_question"] = q

# -----------------------------
# 기존 대화 출력
# -----------------------------
for msg in st.session_state.messages:
    box_class = "user-box" if msg["role"] == "user" else "bot-box"
    st.markdown(f'<div class="{box_class}">{msg["content"]}</div>', unsafe_allow_html=True)

# -----------------------------
# 입력
# -----------------------------
user_input = st.chat_input("예: 배달이랑 외식 혜택 좋은 신용카드 추천해줘")

if "quick_question" in st.session_state:
    user_input = st.session_state["quick_question"]
    del st.session_state["quick_question"]

# -----------------------------
# 응답 처리
# -----------------------------
if user_input:
    st.session_state.messages.append({"role": "user", "content": user_input})
    st.markdown(f'<div class="user-box">{user_input}</div>', unsafe_allow_html=True)

    with st.spinner("카드를 분석하고 추천 중입니다..."):
        try:
            answer = ask_card_bot(
                question=user_input,
                session_id=st.session_state.session_id
            )
            cards = get_recommendation_cards(user_input)
            st.session_state.latest_cards = cards

        except Exception as e:
            answer = f"오류가 발생했습니다: {e}"
            st.session_state.latest_cards = []

    st.session_state.messages.append({"role": "assistant", "content": answer})
    st.markdown(f'<div class="bot-box">{answer}</div>', unsafe_allow_html=True)

# -----------------------------
# 카드형 추천 UI
# -----------------------------
if st.session_state.latest_cards:
    st.markdown('<div class="section-title">추천 카드 TOP 3</div>', unsafe_allow_html=True)

    cols = st.columns(3)

    for idx, card in enumerate(st.session_state.latest_cards[:3]):
        with cols[idx]:
            st.markdown('<div class="card-wrap">', unsafe_allow_html=True)
            st.markdown(f'<div class="card-rank">TOP {idx+1}</div>', unsafe_allow_html=True)

            image_url = card.get("image_url", "")
            if image_url and image_url != "정보없음":
                st.image(image_url, use_container_width=True)
            else:
                st.markdown('<div class="empty-image">CARD IMAGE</div>', unsafe_allow_html=True)

            st.markdown(
                f'<div class="card-name">{card.get("card_name", "이름 없음")}</div>',
                unsafe_allow_html=True
            )

            st.markdown(
                f'''
                <div class="card-meta">
                <b>연회비</b> : {card.get("annual_fee", "정보없음")}<br>
                <b>전월실적</b> : {card.get("performance", "정보없음")}
                </div>
                ''',
                unsafe_allow_html=True
            )

            st.markdown('<div class="card-benefit-title">핵심 혜택 요약</div>', unsafe_allow_html=True)
            st.markdown(
                f'<div class="card-benefit">{card.get("benefit_summary", "정보없음")}</div>',
                unsafe_allow_html=True
            )

            st.markdown('</div>', unsafe_allow_html=True)
