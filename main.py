import os
import re
import html
import streamlit as st
from dotenv import load_dotenv

from openai import OpenAI
from utils_db import load_rag_resources
from recommender import build_context, check_moderation, advanced_retriever_with_rerank

from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser
from langchain_community.chat_message_histories import ChatMessageHistory
from langchain_core.runnables.history import RunnableWithMessageHistory


# =========================================================
# 기본 설정
# =========================================================
st.set_page_config(
    page_title="CardMate AI",
    page_icon="💳",
    layout="wide",
    initial_sidebar_state="expanded",
)

load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY") or st.secrets.get("OPENAI_API_KEY")
GDRIVE_DB_FILE_ID = os.getenv("GDRIVE_DB_FILE_ID") or st.secrets.get("GDRIVE_DB_FILE_ID")

if not OPENAI_API_KEY:
    st.error("OPENAI_API_KEY가 설정되지 않았습니다.")
    st.stop()

if not GDRIVE_DB_FILE_ID:
    st.error("GDRIVE_DB_FILE_ID가 설정되지 않았습니다.")
    st.stop()


# =========================================================
# 스타일
# =========================================================
st.markdown(
    """
    <style>
    :root {
        --bg: #f5f7fb;
        --panel: #ffffff;
        --text: #191f28;
        --muted: #6b7684;
        --line: #e5e8eb;
        --primary: #3182f6;
        --primary-soft: #eaf3ff;
        --shadow: 0 10px 28px rgba(15, 23, 42, 0.07);
    }

    .stApp {
        background: linear-gradient(180deg, #f8fbff 0%, #f4f6fa 100%);
        color: var(--text);
    }

    .block-container {
        max-width: 1320px;
        padding-top: 1.3rem;
        padding-bottom: 2rem;
    }

    section[data-testid="stSidebar"] {
        background: rgba(255,255,255,0.84);
        backdrop-filter: blur(14px);
        border-right: 1px solid rgba(229,232,235,0.9);
    }

    .hero-wrap {
        background: linear-gradient(135deg, #0f5fd8 0%, #3182f6 48%, #75b1ff 100%);
        border-radius: 32px;
        padding: 30px;
        box-shadow: 0 18px 44px rgba(49,130,246,0.22);
        color: white;
        margin-bottom: 20px;
        position: relative;
        overflow: hidden;
    }

    .hero-wrap::after {
        content: "";
        position: absolute;
        width: 320px;
        height: 320px;
        right: -90px;
        top: -110px;
        background: rgba(255,255,255,0.14);
        border-radius: 50%;
    }

    .hero-chip {
        display: inline-flex;
        align-items: center;
        gap: 8px;
        background: rgba(255,255,255,0.15);
        border: 1px solid rgba(255,255,255,0.18);
        padding: 7px 12px;
        border-radius: 999px;
        font-size: 13px;
        margin-bottom: 14px;
        font-weight: 600;
    }

    .hero-title {
        font-size: 35px;
        font-weight: 800;
        line-height: 1.2;
        margin-bottom: 8px;
        letter-spacing: -0.03em;
    }

    .hero-sub {
        font-size: 15px;
        color: rgba(255,255,255,0.93);
        line-height: 1.68;
    }

    .info-grid {
        display: grid;
        grid-template-columns: repeat(3, minmax(0, 1fr));
        gap: 14px;
        margin: 18px 0 18px 0;
    }

    .info-card {
        background: rgba(255,255,255,0.9);
        border: 1px solid rgba(229,232,235,0.95);
        border-radius: 22px;
        padding: 18px;
        box-shadow: var(--shadow);
    }

    .info-label {
        font-size: 12px;
        color: var(--muted);
        margin-bottom: 6px;
        font-weight: 700;
    }

    .info-value {
        font-size: 22px;
        font-weight: 800;
        color: var(--text);
        letter-spacing: -0.02em;
    }

    .info-desc {
        margin-top: 6px;
        color: var(--muted);
        font-size: 13px;
        line-height: 1.5;
    }

    .section-title {
        font-size: 22px;
        font-weight: 800;
        color: var(--text);
        margin: 10px 0 12px 2px;
        letter-spacing: -0.02em;
    }

    .chat-shell {
        background: rgba(255,255,255,0.9);
        border: 1px solid rgba(229,232,235,0.95);
        border-radius: 26px;
        box-shadow: var(--shadow);
        padding: 12px 12px 14px 12px;
    }

    .recommend-scroll {
        display: flex;
        gap: 16px;
        overflow-x: auto;
        padding: 6px 2px 12px 2px;
        scroll-snap-type: x mandatory;
        margin-bottom: 12px;
    }

    .recommend-scroll::-webkit-scrollbar {
        height: 10px;
    }

    .recommend-scroll::-webkit-scrollbar-thumb {
        background: #d4dbe3;
        border-radius: 999px;
    }

    .card-item {
        min-width: 320px;
        max-width: 320px;
        background: linear-gradient(180deg, #ffffff 0%, #fbfcff 100%);
        border: 1px solid #e8edf4;
        border-radius: 24px;
        box-shadow: 0 12px 28px rgba(15, 23, 42, 0.07);
        padding: 18px;
        scroll-snap-align: start;
    }

    .card-rank {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        background: #eef5ff;
        color: #1b64da;
        border-radius: 999px;
        padding: 6px 10px;
        font-size: 12px;
        font-weight: 800;
        margin-bottom: 12px;
    }

    .card-image-wrap {
        width: 100%;
        height: 190px;
        border-radius: 20px;
        background: linear-gradient(135deg, #edf3ff 0%, #f7faff 100%);
        display: flex;
        align-items: center;
        justify-content: center;
        overflow: hidden;
        border: 1px solid #edf2f7;
        margin-bottom: 14px;
    }

    .card-image-wrap img {
        width: 100%;
        height: 100%;
        object-fit: contain;
    }

    .card-image-fallback {
        width: 92px;
        height: 92px;
        border-radius: 22px;
        background: linear-gradient(135deg, #1b64da 0%, #7db8ff 100%);
        display: flex;
        align-items: center;
        justify-content: center;
        color: white;
        font-size: 36px;
        font-weight: 800;
        box-shadow: 0 10px 24px rgba(49,130,246,0.25);
    }

    .card-name {
        font-size: 20px;
        font-weight: 800;
        color: var(--text);
        line-height: 1.35;
        margin-bottom: 10px;
        letter-spacing: -0.02em;
    }

    .badge-row {
        display: flex;
        gap: 8px;
        flex-wrap: wrap;
        margin-bottom: 12px;
    }

    .badge {
        font-size: 11px;
        font-weight: 700;
        padding: 7px 10px;
        border-radius: 999px;
        border: 1px solid #e6ebf0;
        color: #4e5968;
        background: #fafbfd;
    }

    .card-benefit {
        font-size: 14px;
        line-height: 1.7;
        color: #333d4b;
        background: #f8fafc;
        border: 1px solid #edf2f7;
        border-radius: 16px;
        padding: 12px 14px;
        min-height: 104px;
        margin-bottom: 12px;
    }

    .card-mini {
        font-size: 13px;
        line-height: 1.7;
        color: var(--muted);
        background: #fcfdff;
        border: 1px dashed #e5e8eb;
        border-radius: 16px;
        padding: 12px 14px;
    }

    .empty-card {
        background: rgba(255,255,255,0.92);
        border: 1px dashed #d7dfe7;
        border-radius: 20px;
        padding: 22px;
        color: var(--muted);
        text-align: center;
    }

    .side-card {
        background: rgba(255,255,255,0.92);
        border: 1px solid rgba(229,232,235,0.95);
        border-radius: 20px;
        padding: 16px;
        box-shadow: var(--shadow);
        margin-bottom: 12px;
    }

    .side-title {
        font-size: 15px;
        font-weight: 800;
        color: var(--text);
        margin-bottom: 8px;
    }

    .side-desc {
        font-size: 13px;
        color: var(--muted);
        line-height: 1.6;
    }

    .quick-chip {
        display: inline-block;
        background: var(--primary-soft);
        color: var(--primary);
        padding: 8px 12px;
        border-radius: 999px;
        font-size: 12px;
        font-weight: 700;
        margin: 4px 6px 0 0;
        border: 1px solid #d9e8ff;
    }

    div[data-testid="stChatMessage"] {
        border-radius: 18px;
        padding: 4px 6px;
        margin-bottom: 8px;
    }

    div[data-testid="stChatMessage"] [data-testid="stMarkdownContainer"] p,
    div[data-testid="stChatMessage"] [data-testid="stMarkdownContainer"] li {
        line-height: 1.78;
        font-size: 15px;
    }

    .stChatInput > div {
        border-radius: 20px !important;
        border: 1px solid #dbe2ea !important;
        box-shadow: 0 8px 24px rgba(15,23,42,0.05) !important;
        background: rgba(255,255,255,0.96) !important;
    }

    .stButton > button {
        width: 100%;
        border-radius: 14px;
        height: 42px;
        border: 1px solid #d9e8ff;
        background: #eff6ff;
        color: #1b64da;
        font-weight: 700;
    }

    .stButton > button:hover {
        border-color: #bfd7ff;
        background: #e6f0ff;
        color: #155ac8;
    }

    @media (max-width: 1100px) {
        .info-grid {
            grid-template-columns: 1fr;
        }
        .card-item {
            min-width: 280px;
            max-width: 280px;
        }
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# =========================================================
# 유틸
# =========================================================
def safe_text(value, default="정보 없음"):
    if value is None:
        return default
    text = str(value).strip()
    if not text or text.lower() == "nan":
        return default
    return text


def get_card_image_url(card_name: str, all_cards_from_db: dict) -> str:
    if not isinstance(all_cards_from_db, dict):
        return ""
    card = all_cards_from_db.get(card_name, {})
    return (
        card.get("Image_URL")
        or card.get("image_url")
        or card.get("image")
        or ""
    )


def extract_card_name(block: str) -> str:
    match = re.search(r"###\s*(.*?)\s*###", block)
    return safe_text(match.group(1), "추천 카드") if match else "추천 카드"


def extract_rank(block: str, fallback_rank: int) -> int:
    match = re.search(r"추천\s*(\d+)순위", block)
    return int(match.group(1)) if match else fallback_rank


def extract_fee_perf(block: str):
    fee = "정보 없음"
    perf = "정보 없음"
    match = re.search(r"\[조건\]\s*연회비:\s*(.*?)\s*/\s*전월실적:\s*(.*)", block, re.DOTALL)
    if match:
        fee = safe_text(match.group(1))
        perf = safe_text(match.group(2))
    return fee, perf


def extract_benefit(block: str) -> str:
    cleaned = re.sub(r"\[\[.*?\]\]", "", block, flags=re.DOTALL)
    cleaned = re.sub(r"###\s*.*?\s*###", "", cleaned, flags=re.DOTALL)
    cleaned = re.sub(r"\[조건\].*", "", cleaned, flags=re.DOTALL)
    cleaned = cleaned.strip()
    if not cleaned:
        return "질문과 가장 관련된 혜택 정보를 기반으로 추천되었습니다."
    return cleaned[:240] + ("..." if len(cleaned) > 240 else "")


def parse_context_cards(context: str, all_cards_from_db: dict):
    if not context or "검색된 카드 정보가 없습니다" in context:
        return []

    blocks = re.split(r"\n(?=\[\[🔥 추천 \d+순위 문서 🔥\]\])", context.strip())
    cards = []

    for idx, block in enumerate([b for b in blocks if b.strip()], start=1):
        card_name = extract_card_name(block)
        fee, perf = extract_fee_perf(block)
        cards.append(
            {
                "rank": extract_rank(block, idx),
                "card_name": card_name,
                "image_url": get_card_image_url(card_name, all_cards_from_db),
                "benefit": extract_benefit(block),
                "fee": fee,
                "perf": perf,
                "card_type": safe_text(
                    all_cards_from_db.get(card_name, {}).get("Card_Type")
                    or all_cards_from_db.get(card_name, {}).get("card_type"),
                    "카드",
                ),
            }
        )
    return cards


def render_card_carousel(cards):
    st.markdown('<div class="section-title">추천 카드</div>', unsafe_allow_html=True)

    if not cards:
        st.markdown(
            '<div class="empty-card">아직 추천 카드가 없어요. 원하는 혜택을 입력하면 카드 이미지와 함께 추천 결과가 여기에 표시됩니다.</div>',
            unsafe_allow_html=True,
        )
        return

    html_parts = ['<div class="recommend-scroll">']
    for card in cards:
        card_name = html.escape(safe_text(card.get("card_name"), "추천 카드"))
        image_url = safe_text(card.get("image_url"), "")
        card_type = html.escape(safe_text(card.get("card_type"), "카드"))
        fee = html.escape(safe_text(card.get("fee"), "정보 없음"))
        perf = html.escape(safe_text(card.get("perf"), "정보 없음"))
        benefit = html.escape(safe_text(card.get("benefit"), "추천 혜택 정보"))
        rank = card.get("rank", 0)

        if image_url and image_url.startswith("http"):
            image_html = f'<img src="{html.escape(image_url)}" alt="{card_name}">'  # nosec B703
        else:
            first_char = html.escape(card_name[:1] if card_name else "💳")
            image_html = f'<div class="card-image-fallback">{first_char}</div>'

        html_parts.append(
            f"""
            <div class="card-item">
                <div class="card-rank">✨ 추천 {rank}순위</div>
                <div class="card-image-wrap">{image_html}</div>
                <div class="card-name">{card_name}</div>
                <div class="badge-row">
                    <span class="badge">{card_type}</span>
                    <span class="badge">연회비 {fee}</span>
                    <span class="badge">실적 {perf}</span>
                </div>
                <div class="card-benefit"><b>핵심 혜택</b><br>{benefit}</div>
                <div class="card-mini"><b>포인트</b><br>추천 결과 텍스트와 함께 비교해 보면서 가장 잘 맞는 카드를 골라보세요.</div>
            </div>
            """
        )
    html_parts.append("</div>")
    st.markdown("".join(html_parts), unsafe_allow_html=True)


def render_hero(total_cards: int, db_path: str):
    st.markdown(
        """
        <div class="hero-wrap">
            <div class="hero-chip">✨ AI 카드 추천 · Hybrid RAG · Toss Style</div>
            <div class="hero-title">내 소비패턴에 딱 맞는 카드,<br>서비스처럼 빠르게 추천받기</div>
            <div class="hero-sub">카드 혜택 DB를 검색해서 카드 이미지, 핵심 혜택, 연회비, 전월실적을 함께 보여줍니다. 원하는 생활 패턴을 편하게 입력해 보세요.</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    db_name = html.escape(db_path.split("/")[-1] if db_path else "semantic db")
    st.markdown(
        f"""
        <div class="info-grid">
            <div class="info-card">
                <div class="info-label">추천 엔진</div>
                <div class="info-value">Hybrid RAG</div>
                <div class="info-desc">BM25와 벡터 검색을 함께 사용해 질문에 더 잘 맞는 카드 후보를 찾습니다.</div>
            </div>
            <div class="info-card">
                <div class="info-label">카드 혜택 청크</div>
                <div class="info-value">{total_cards:,}</div>
                <div class="info-desc">로드된 문서를 바탕으로 추천 카드를 압축해서 보여줍니다.</div>
            </div>
            <div class="info-card">
                <div class="info-label">DB 상태</div>
                <div class="info-value">{db_name}</div>
                <div class="info-desc">구글드라이브 zip DB를 현재 세션에서 불러와 사용하고 있습니다.</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


# =========================================================
# 리소스 로드
# =========================================================
@st.cache_resource(show_spinner=True)
def init_services():
    client = OpenAI(api_key=OPENAI_API_KEY)
    llm = ChatOpenAI(
        model_name="gpt-3.5-turbo",
        api_key=OPENAI_API_KEY,
        temperature=0.1,
    )
    rag_resources = load_rag_resources(
        openai_api_key=OPENAI_API_KEY,
        gdrive_db_file_id=GDRIVE_DB_FILE_ID,
    )
    return client, llm, rag_resources


try:
    client, llm, rag_resources = init_services()
    db_path = rag_resources.get("db_path", "")
    documents = rag_resources["documents"]
    bm25_retriever = rag_resources["bm25_retriever"]
    vector_retriever = rag_resources["vector_retriever"]
    all_cards_from_db = rag_resources["all_cards_from_db"]
except Exception as e:
    st.error(f"초기 리소스 로드 실패: {e}")
    st.stop()


# =========================================================
# 프롬프트 / 체인 연결
# =========================================================
base_prompt = ChatPromptTemplate.from_messages(
    [
        ("system", get_system_prompt()),
        MessagesPlaceholder(variable_name="history"),
        ("human", "{question}"),
    ]
)

base_chain = (
    RunnablePassthrough.assign(
        context=lambda x: build_context(
            question=x["question"],
            bm25_retriever=bm25_retriever,
            vector_retriever=vector_retriever,
            documents=documents,
            all_cards_from_db=all_cards_from_db,
        )
    )
    | base_prompt
    | llm
    | StrOutputParser()
)

store = {}


def get_session_history(session_id: str):
    if session_id not in store:
        store[session_id] = ChatMessageHistory()
    return store[session_id]


conversational_chain = RunnableWithMessageHistory(
    base_chain,
    get_session_history,
    input_messages_key="question",
    history_messages_key="history",
)


# =========================================================
# 세션 상태
# =========================================================
if "session_id" not in st.session_state:
    st.session_state.session_id = "cardmate_session"

if "messages" not in st.session_state:
    st.session_state.messages = [
        {
            "role": "assistant",
            "content": "안녕하세요. 카드 사용 패턴에 맞게 혜택 좋은 카드를 찾아드릴게요. 예를 들어 '배달이랑 외식 할인 좋은 신용카드 추천해줘'처럼 말해보세요.",
        }
    ]

if "latest_cards" not in st.session_state:
    st.session_state.latest_cards = []

if "prefill_prompt" not in st.session_state:
    st.session_state.prefill_prompt = ""


# =========================================================
# 사이드바
# =========================================================
with st.sidebar:
    st.markdown('<div class="side-card"><div class="side-title">💳 CardMate AI</div><div class="side-desc">카드 추천 로직과 프롬프트는 별도 파일에서 관리하고, 여기서는 서비스형 UI와 결과 표현에 집중합니다.</div></div>', unsafe_allow_html=True)

    st.markdown('<div class="side-card"><div class="side-title">빠른 시작</div><div class="side-desc">아래 버튼을 누르면 추천 문장이 입력창으로 바로 들어갑니다.</div></div>', unsafe_allow_html=True)

    quick_prompts = [
        "나 18살 학생인데 편의점이랑 교통비 할인 많이 되는 체크카드 추천해줘",
        "배달이랑 외식 혜택 좋은 신용카드 추천해줘",
        "전월실적 부담 적은 카드 추천해줘",
        "해외여행 마일리지 적립 좋은 카드 추천해줘",
        "인기있는 카드 3개 추천해줘",
    ]

    for prompt in quick_prompts:
        if st.button(prompt):
            st.session_state.prefill_prompt = prompt

    st.markdown('<div class="side-card"><div class="side-title">질문 팁</div><div class="side-desc">원하는 카드 종류, 자주 쓰는 곳, 혜택 방향을 같이 적으면 더 정확해져요.<br><br><span class="quick-chip">체크카드</span><span class="quick-chip">편의점</span><span class="quick-chip">교통</span><span class="quick-chip">무실적</span></div></div>', unsafe_allow_html=True)


# =========================================================
# 메인 레이아웃
# =========================================================
render_hero(total_cards=len(documents), db_path=db_path)

left_col, right_col = st.columns([1.04, 1.36], gap="large")

with left_col:
    render_card_carousel(st.session_state.latest_cards)

with right_col:
    st.markdown('<div class="section-title">추천 결과 텍스트</div>', unsafe_allow_html=True)
    st.markdown('<div class="chat-shell">', unsafe_allow_html=True)
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
    st.markdown('</div>', unsafe_allow_html=True)


# =========================================================
# 실행
# =========================================================
def run_assistant(question: str) -> str:
    moderation_result = check_moderation(client, question)
    if moderation_result.get("flagged"):
        st.session_state.latest_cards = []
        return "부적절한 내용이 포함되어 있어 답변할 수 없습니다. 다른 방식으로 질문해 주세요."

    docs = advanced_retriever_with_rerank(
        query=question,
        bm25_retriever=bm25_retriever,
        vector_retriever=vector_retriever,
        documents=documents,
        all_cards_from_db=all_cards_from_db,
    )

    if not docs:
        st.session_state.latest_cards = []
        return "조건에 맞는 카드 정보를 찾지 못했어요. 원하는 혜택이나 카드 종류를 조금 더 구체적으로 입력해 주세요."

    context = build_context(
        question=question,
        bm25_retriever=bm25_retriever,
        vector_retriever=vector_retriever,
        documents=documents,
        all_cards_from_db=all_cards_from_db,
    )
    st.session_state.latest_cards = parse_context_cards(context, all_cards_from_db)

    return conversational_chain.invoke(
        {"question": question},
        config={"configurable": {"session_id": st.session_state.session_id}},
    )


chat_placeholder = (
    st.session_state.prefill_prompt
    if st.session_state.prefill_prompt
    else "예: 나 18살 학생인데 교통비랑 편의점 할인 좋은 체크카드 추천해줘"
)
user_prompt = st.chat_input(chat_placeholder)

if st.session_state.prefill_prompt and not user_prompt:
    user_prompt = st.session_state.prefill_prompt
    st.session_state.prefill_prompt = ""

if user_prompt:
    st.session_state.messages.append({"role": "user", "content": user_prompt})

    with right_col:
        with st.chat_message("user"):
            st.markdown(user_prompt)
        with st.chat_message("assistant"):
            with st.spinner("카드 혜택을 분석하고 있어요..."):
                try:
                    answer = run_assistant(user_prompt)
                    st.markdown(answer)
                except Exception as e:
                    answer = f"실행 중 오류가 발생했습니다: {e}"
                    st.error(answer)

    st.session_state.messages.append({"role": "assistant", "content": answer})
    st.rerun()
