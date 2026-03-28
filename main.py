import html
import streamlit as st
import recommender as rc


st.set_page_config(
    page_title="CardMate AI",
    page_icon="💳",
    layout="wide",
    initial_sidebar_state="expanded",
)

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
        padding-top: 1.2rem;
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
        min-height: 540px;
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


@st.cache_resource(show_spinner=False)
def ensure_recommender_loaded():
    return rc


def safe_text(value, default="정보 없음"):
    if value is None:
        return default
    text = str(value).strip()
    if not text or text.lower() == "nan":
        return default
    return text


def get_card_image_url(doc):
    meta = getattr(doc, "metadata", {}) or {}
    image_url = (
        meta.get("Image_URL")
        or meta.get("image_url")
        or meta.get("image")
        or meta.get("card_image")
        or meta.get("img_url")
        or ""
    )

    if image_url:
        return image_url

    card_name = meta.get("card_name")
    all_cards = getattr(rc, "all_cards_from_db", {})
    if card_name and isinstance(all_cards, dict):
        card_meta = all_cards.get(card_name, {})
        return (
            card_meta.get("Image_URL")
            or card_meta.get("image_url")
            or card_meta.get("image")
            or ""
        )
    return ""


def extract_preview_text(doc):
    page = safe_text(getattr(doc, "page_content", ""), "")
    if not page:
        return "질문과 가장 관련된 카드로 추천되었어요."
    preview = page.replace("\n", " ").strip()
    return preview[:220] + ("..." if len(preview) > 220 else "")


def docs_to_cards(docs):
    cards = []
    for idx, doc in enumerate(docs, start=1):
        meta = getattr(doc, "metadata", {}) or {}
        cards.append(
            {
                "rank": idx,
                "card_name": safe_text(meta.get("card_name"), f"추천 카드 {idx}"),
                "card_type": safe_text(meta.get("card_type"), "카드"),
                "fee": safe_text(meta.get("annual_fee"), "정보없음"),
                "perf": safe_text(meta.get("performance"), "정보없음"),
                "image_url": get_card_image_url(doc),
                "benefit": extract_preview_text(doc),
            }
        )
    return cards


def render_card_carousel(cards):
    st.markdown('<div class="section-title">추천 카드</div>', unsafe_allow_html=True)

    if not cards:
        st.markdown(
            '<div class="empty-card">아직 추천 카드가 없어요. 원하는 혜택을 입력하면 카드 이미지와 함께 결과가 여기에 표시됩니다.</div>',
            unsafe_allow_html=True,
        )
        return

    html_parts = ['<div class="recommend-scroll">']
    for card in cards:
        card_name = html.escape(safe_text(card.get("card_name"), "추천 카드"))
        image_url = safe_text(card.get("image_url"), "")
        card_type = html.escape(safe_text(card.get("card_type"), "카드"))
        fee = html.escape(safe_text(card.get("fee"), "정보없음"))
        perf = html.escape(safe_text(card.get("perf"), "정보없음"))
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
                <div class="card-mini"><b>추천 포인트</b><br>오른쪽 추천 결과 텍스트와 함께 비교해서 가장 잘 맞는 카드를 골라보세요.</div>
            </div>
            """
        )
    html_parts.append("</div>")
    st.markdown("".join(html_parts), unsafe_allow_html=True)


def render_hero(total_cards):
    st.markdown(
        """
        <div class="hero-wrap">
            <div class="hero-chip">✨ AI 카드 추천 · Hybrid RAG · Toss Style</div>
            <div class="hero-title">내 소비패턴에 딱 맞는 카드,<br>서비스처럼 빠르게 추천받기</div>
            <div class="hero-sub">recommender.py의 모델과 검색 체인을 그대로 사용하고, 여기서는 카드 이미지와 추천 결과를 보기 좋게 보여줍니다.</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(
        f"""
        <div class="info-grid">
            <div class="info-card">
                <div class="info-label">추천 엔진</div>
                <div class="info-value">Hybrid RAG</div>
                <div class="info-desc">BM25와 벡터 검색을 함께 사용해 질문에 더 잘 맞는 카드 후보를 찾습니다.</div>
            </div>
            <div class="info-card">
                <div class="info-label">로드된 문서 수</div>
                <div class="info-value">{total_cards:,}</div>
                <div class="info-desc">semantic 청킹된 카드 혜택 문서를 기반으로 추천합니다.</div>
            </div>
            <div class="info-card">
                <div class="info-label">출력 구성</div>
                <div class="info-value">텍스트 + 이미지</div>
                <div class="info-desc">프롬프트 형식에 맞는 추천 텍스트와 카드 이미지 슬라이드를 동시에 보여줍니다.</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


module = ensure_recommender_loaded()

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

with st.sidebar:
    st.markdown('<div class="side-card"><div class="side-title">💳 CardMate AI</div><div class="side-desc">모델과 검색 로직은 recommender.py에서 실행하고, main.py는 서비스형 UI와 카드 이미지 결과를 담당합니다.</div></div>', unsafe_allow_html=True)

    st.markdown('<div class="side-card"><div class="side-title">빠른 시작</div><div class="side-desc">아래 버튼을 누르면 질문이 바로 입력됩니다.</div></div>', unsafe_allow_html=True)

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

    st.markdown('<div class="side-card"><div class="side-title">질문 팁</div><div class="side-desc">원하는 카드 종류, 자주 쓰는 곳, 혜택 방향을 함께 적어보세요.<br><br><span class="quick-chip">체크카드</span><span class="quick-chip">편의점</span><span class="quick-chip">교통</span><span class="quick-chip">무실적</span></div></div>', unsafe_allow_html=True)

render_hero(total_cards=len(getattr(module, "documents", [])))

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


def run_assistant(question: str):
    moderation_result = module.check_moderation(question)
    if moderation_result.get("flagged"):
        st.session_state.latest_cards = []
        return "부적절한 내용이 포함되어 있어 답변할 수 없습니다. 다른 방식으로 질문해 주세요.", []

    docs = module.advanced_retriever_with_rerank(question)
    if not docs:
        st.session_state.latest_cards = []
        return "조건에 맞는 카드 정보를 찾지 못했어요. 원하는 혜택이나 카드 종류를 조금 더 구체적으로 입력해 주세요.", []

    cards = docs_to_cards(docs)
    config = {"configurable": {"session_id": st.session_state.session_id}}
    answer = module.chat(question, config)
    return answer, cards


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
                    answer, cards = run_assistant(user_prompt)
                    st.session_state.latest_cards = cards
                    st.markdown(answer)
                except Exception as e:
                    st.session_state.latest_cards = []
                    answer = f"실행 중 오류가 발생했습니다: {e}"
                    st.error(answer)

    st.session_state.messages.append({"role": "assistant", "content": answer})
    st.rerun()
