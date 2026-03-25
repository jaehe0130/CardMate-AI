import streamlit as st
from utils import (
    load_card_data,
    get_card_image,
    get_card_name,
    get_card_company,
    get_card_type,
    get_card_benefit,
    get_card_annual_fee,
    get_card_perf,
    get_card_brands,
    get_card_url,
    summarize_user_profile,
)
from recommender import recommend_cards

st.set_page_config(
    page_title="CardMate AI",
    page_icon="💳",
    layout="centered",
    initial_sidebar_state="collapsed"
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Pretendard:wght@400;500;600;700;800&display=swap');

html, body, [class*="css"] {
    font-family: 'Pretendard', sans-serif;
}

.stApp {
    background-color: #f5f6f8;
}

.block-container {
    max-width: 430px;
    padding-top: 1rem;
    padding-bottom: 1rem;
}

.app-title {
    font-size: 1.9rem;
    font-weight: 800;
    color: #111111;
    margin-bottom: 0.2rem;
}

.app-subtitle {
    color: #666666;
    font-size: 0.95rem;
    margin-bottom: 1rem;
}

.app-shell {
    background: #ffffff;
    border: 1px solid #e9e9e9;
    border-radius: 28px;
    padding: 18px 16px 20px 16px;
    min-height: 700px;
    box-shadow: 0 10px 30px rgba(0,0,0,0.05);
}

.bot-bubble {
    background: #f2f3f5;
    color: #111111;
    padding: 14px 16px;
    border-radius: 18px 18px 18px 6px;
    margin-bottom: 10px;
    width: fit-content;
    max-width: 90%;
    font-size: 0.96rem;
    line-height: 1.45;
}

.user-bubble {
    background: #111111;
    color: white;
    padding: 14px 16px;
    border-radius: 18px 18px 6px 18px;
    margin: 10px 0 10px auto;
    width: fit-content;
    max-width: 85%;
    font-size: 0.96rem;
    line-height: 1.45;
}

.card-box {
    background: #ffffff;
    border: 1px solid #ededed;
    border-radius: 22px;
    padding: 15px;
    margin-top: 12px;
    box-shadow: 0 4px 12px rgba(0,0,0,0.04);
}

.card-title {
    font-size: 1.05rem;
    font-weight: 700;
    color: #111;
    margin-bottom: 4px;
}

.card-sub {
    color: #666;
    font-size: 0.88rem;
    margin-bottom: 8px;
}

.tag {
    display: inline-block;
    padding: 5px 10px;
    border-radius: 999px;
    background: #f2f3f5;
    color: #333;
    font-size: 0.78rem;
    margin-right: 6px;
    margin-top: 6px;
}
</style>
""", unsafe_allow_html=True)

@st.cache_data
def get_cards():
    return load_card_data()

cards = get_cards()

if "step" not in st.session_state:
    st.session_state.step = 0

if "answers" not in st.session_state:
    st.session_state.answers = {
        "card_type": None,
        "main_use": None,
        "monthly_spend": None,
        "extra_use": None,
    }

if "recommended_cards" not in st.session_state:
    st.session_state.recommended_cards = []

st.markdown('<div class="app-title">CardMate AI</div>', unsafe_allow_html=True)
st.markdown('<div class="app-subtitle">카드사 챗봇처럼 몇 가지 질문 후 맞춤 카드를 추천해드려요.</div>', unsafe_allow_html=True)

st.markdown('<div class="app-shell">', unsafe_allow_html=True)

st.markdown(
    '<div class="bot-bubble"><b>무엇을 도와드릴까요?</b><br>간단한 질문 몇 개만 답해주시면 어울리는 카드를 추천해드릴게요.</div>',
    unsafe_allow_html=True
)

quick_cols = st.columns(3)
quick_buttons = ["카페", "교통", "해외결제"]

for idx, item in enumerate(quick_buttons):
    with quick_cols[idx]:
        if st.button(item, use_container_width=True):
            st.session_state.answers["main_use"] = item
            if st.session_state.answers["card_type"] is None:
                st.session_state.answers["card_type"] = "상관없음"
            st.session_state.step = 2
            st.rerun()

if st.session_state.step == 0:
    st.markdown('<div class="bot-bubble">1. 어떤 카드가 필요하신가요?</div>', unsafe_allow_html=True)

    selected = st.radio(
        "카드 종류",
        ["신용카드", "체크카드", "상관없음"],
        label_visibility="collapsed"
    )

    if st.button("다음", use_container_width=True):
        st.session_state.answers["card_type"] = selected
        st.session_state.step = 1
        st.rerun()

elif st.session_state.step == 1:
    st.markdown(f'<div class="user-bubble">{st.session_state.answers.get("card_type")}</div>', unsafe_allow_html=True)
    st.markdown('<div class="bot-bubble">2. 카드를 주로 어디에 사용하실 예정인가요?</div>', unsafe_allow_html=True)

    selected = st.selectbox(
        "주 사용 업종",
        ["카페", "편의점", "교통", "쇼핑", "해외결제", "배달", "통신"],
        label_visibility="collapsed"
    )

    if st.button("다음 단계", use_container_width=True):
        st.session_state.answers["main_use"] = selected
        st.session_state.step = 2
        st.rerun()

elif st.session_state.step == 2:
    st.markdown(f'<div class="user-bubble">{st.session_state.answers.get("main_use", "미선택")}</div>', unsafe_allow_html=True)
    st.markdown('<div class="bot-bubble">3. 월 카드 사용액은 어느 정도인가요?</div>', unsafe_allow_html=True)

    selected = st.radio(
        "월 사용액",
        ["30만원 이하", "30~70만원", "70만원 이상"],
        label_visibility="collapsed"
    )

    if st.button("다음 질문", use_container_width=True):
        st.session_state.answers["monthly_spend"] = selected
        st.session_state.step = 3
        st.rerun()

elif st.session_state.step == 3:
    st.markdown(f'<div class="user-bubble">{st.session_state.answers.get("monthly_spend")}</div>', unsafe_allow_html=True)
    st.markdown('<div class="bot-bubble">4. 추가로 자주 쓰는 업종이 있다면 하나 더 골라주세요.</div>', unsafe_allow_html=True)

    selected = st.selectbox(
        "추가 업종",
        ["카페", "편의점", "교통", "쇼핑", "해외결제", "배달", "통신"],
        label_visibility="collapsed"
    )

    if st.button("추천 받기", use_container_width=True):
        st.session_state.answers["extra_use"] = selected
        st.session_state.recommended_cards = recommend_cards(
            cards,
            st.session_state.answers,
            top_k=3
        )
        st.session_state.step = 4
        st.rerun()

elif st.session_state.step == 4:
    st.markdown(f'<div class="user-bubble">{st.session_state.answers.get("extra_use")}</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="bot-bubble"><b>추천 카드 3개를 찾았어요.</b><br>혜택과 전월 실적을 함께 확인해보세요.</div>',
        unsafe_allow_html=True
    )

    st.info(summarize_user_profile(st.session_state.answers))

    for card in st.session_state.recommended_cards:
        st.markdown('<div class="card-box">', unsafe_allow_html=True)

        image_url = get_card_image(card)
        if image_url:
            st.image(image_url, width=220)

        st.markdown(f'<div class="card-title">{get_card_name(card)}</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="card-sub">{get_card_company(card)} · {get_card_type(card)}</div>', unsafe_allow_html=True)

        st.write(f"**주요 혜택**: {get_card_benefit(card)[:250]}")
        st.write(f"**연회비**: {get_card_annual_fee(card)}")
        st.write(f"**전월 실적**: {get_card_perf(card)}")

        brands = get_card_brands(card)
        for brand in brands[:4]:
            st.markdown(f'<span class="tag">{brand}</span>', unsafe_allow_html=True)

        url = get_card_url(card)
        if url:
            st.link_button("카드 상세 보기", url, use_container_width=True)

        st.markdown('</div>', unsafe_allow_html=True)

    col1, col2 = st.columns(2)

    with col1:
        if st.button("처음부터 다시", use_container_width=True):
            st.session_state.step = 0
            st.session_state.answers = {
                "card_type": None,
                "main_use": None,
                "monthly_spend": None,
                "extra_use": None,
            }
            st.session_state.recommended_cards = []
            st.rerun()

    with col2:
        if st.button("다시 추천", use_container_width=True):
            st.session_state.recommended_cards = recommend_cards(
                cards,
                st.session_state.answers,
                top_k=3
            )
            st.rerun()

st.markdown('</div>', unsafe_allow_html=True)
