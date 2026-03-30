import os
import json
import re
import streamlit as st
from dotenv import load_dotenv
from openai import OpenAI
from langchain_core.documents import Document
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_chroma import Chroma
from langchain_community.retrievers import BM25Retriever
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser
from langchain_community.chat_message_histories import ChatMessageHistory
from langchain_core.runnables.history import RunnableWithMessageHistory

# ─────────────────────────────────────────
# 페이지 설정
# ─────────────────────────────────────────
st.set_page_config(
    page_title="CardMate 💳",
    page_icon="💳",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─────────────────────────────────────────
# CSS 스타일
# ─────────────────────────────────────────
st.markdown(
    """
<style>
    /* 전체 배경 */
    .stApp { background: #f0f4f8; }

    /* 채팅 메시지 버블 */
    .user-bubble {
        background: #4A90D9;
        color: white;
        border-radius: 18px 18px 4px 18px;
        padding: 12px 16px;
        margin: 6px 0;
        max-width: 75%;
        margin-left: auto;
        word-break: break-word;
    }
    .assistant-bubble {
        background: white;
        color: #1a1a2e;
        border-radius: 18px 18px 18px 4px;
        padding: 12px 16px;
        margin: 6px 0;
        max-width: 85%;
        box-shadow: 0 2px 8px rgba(0,0,0,0.08);
        word-break: break-word;
    }

    /* 카드 컨테이너 */
    .card-container {
        display: flex;
        flex-wrap: wrap;
        gap: 16px;
        margin: 16px 0;
    }
    .card-box {
        background: white;
        border-radius: 16px;
        padding: 20px;
        box-shadow: 0 4px 16px rgba(74,144,217,0.15);
        border: 1px solid #e8f0fe;
        flex: 1 1 240px;
        min-width: 220px;
        max-width: 300px;
        transition: transform 0.2s;
    }
    .card-box:hover { transform: translateY(-4px); }
    .card-rank {
        font-size: 11px;
        font-weight: 700;
        color: #4A90D9;
        text-transform: uppercase;
        letter-spacing: 1px;
        margin-bottom: 8px;
    }
    .card-name {
        font-size: 15px;
        font-weight: 700;
        color: #1a1a2e;
        margin-bottom: 12px;
        line-height: 1.3;
    }
    .card-img {
        width: 100%;
        max-height: 140px;
        object-fit: contain;
        border-radius: 8px;
        margin-bottom: 12px;
        background: #f8f9fa;
    }
    .card-badge {
        display: inline-block;
        background: #e8f0fe;
        color: #4A90D9;
        border-radius: 20px;
        padding: 3px 10px;
        font-size: 11px;
        font-weight: 600;
        margin-bottom: 10px;
    }
    .card-benefit {
        font-size: 12px;
        color: #555;
        line-height: 1.6;
    }
    .card-fee {
        font-size: 11px;
        color: #888;
        margin-top: 8px;
        padding-top: 8px;
        border-top: 1px solid #f0f0f0;
    }

    /* 입력창 */
    .stChatInput > div { border-radius: 24px !important; }

    /* 사이드바 */
    section[data-testid="stSidebar"] {
        background: #1a1a2e;
    }
    section[data-testid="stSidebar"] * { color: white !important; }

    /* 3. 버튼 기본 상태 (배경 흰색, 글씨 검은색 강제 고정!) */
    section[data-testid="stSidebar"] .stButton button,
    section[data-testid="stSidebar"] .stButton button * {
        background-color: white !important;
        color: black !important; 
    }
    
    /* 4. 마우스 올렸을 때 (배경 흰색 유지, 글씨 검은색 유지) */
    section[data-testid="stSidebar"] .stButton button:hover,
    section[data-testid="stSidebar"] .stButton button:hover * {
        background-color: lightgray !important; 
        color: black !important;
    }

    /* 헤더 */
    .main-header {
        background: linear-gradient(135deg, #1a1a2e 0%, #4A90D9 100%);
        color: white;
        padding: 24px 32px;
        border-radius: 16px;
        margin-bottom: 24px;
        text-align: center;
    }
    .main-header h1 { margin: 0; font-size: 28px; }
    .main-header p { margin: 6px 0 0; opacity: 0.85; font-size: 14px; }
</style>
""",
    unsafe_allow_html=True,
)


# ─────────────────────────────────────────
# 환경 로드 & 초기화 (캐시)
# ─────────────────────────────────────────
PERSIST_DIR = "./card_semantic_db_v3"
DATA_FILE = "./merged_card_data.json"


def _build_db(embeddings) -> None:
    """merged_card_data.json → Chroma DB 자동 생성 (첫 실행 시 1회만)"""
    import shutil

    if not os.path.exists(DATA_FILE):
        raise FileNotFoundError(
            f"'{DATA_FILE}' 파일을 찾을 수 없습니다. "
            "프로젝트 루트에 merged_card_data.json을 넣어주세요."
        )

    with open(DATA_FILE, "r", encoding="utf-8") as f:
        card_data = json.load(f)

    semantic_docs = []
    for card in card_data:
        card_name = card.get("Card_Name", "이름 없음")
        card_type = card.get("Card_Type", "구분 없음")
        company = card.get("Card_Company", "카드사 없음")
        perf = card.get("Base_Perf_Num", 0)
        fee_dom = card.get("Annual_Fee_Domestic", 0)
        fee_ovs = card.get("Annual_Fee_Overseas", 0)
        image_url = card.get("Image_URL", "")
        rank = int(card.get("Rank", 999))
        benefits = card.get("Benefits_Summary", [])

        base_meta = {
            "card_name": card_name,
            "card_company": company,
            "card_type": card_type,
            "performance": perf,
            "annual_fee": fee_dom,
            "image_url": image_url,
            "rank": rank,
        }

        if not benefits:
            chunk_text = (
                f"카드명: {card_name}\n분류: {card_type}\n"
                f"연회비: 국내 {fee_dom}원, 해외 {fee_ovs}원\n"
                f"이 카드는 특별한 상세 혜택 요약 정보가 없습니다."
            )
            semantic_docs.append(Document(page_content=chunk_text, metadata=base_meta))
            continue

        for b in benefits:
            chunk_text = (
                f"카드명: {card_name}\n분류: {card_type}\n" f"혜택 내용: {b[:350]}"
            )
            semantic_docs.append(Document(page_content=chunk_text, metadata=base_meta))

    Chroma.from_documents(
        documents=semantic_docs,
        embedding=embeddings,
        persist_directory=PERSIST_DIR,
    )


@st.cache_resource(show_spinner="🔧 AI 엔진을 준비하는 중...")
def init_engine(api_key: str):
    """벡터DB, BM25, 체인을 한 번만 초기화합니다. DB가 없으면 자동 생성합니다."""
    client = OpenAI(api_key=api_key)
    embeddings = OpenAIEmbeddings(api_key=api_key, model="text-embedding-3-small")

    # ── DB 자동 생성 ──────────────────────────
    if not os.path.exists(PERSIST_DIR) or not os.listdir(PERSIST_DIR):
        with st.spinner("📦 카드 DB를 처음 구축하는 중입니다... (약 1~3분 소요)"):
            _build_db(embeddings)

    # ── DB 로드 ───────────────────────────────
    vector_db = Chroma(
        persist_directory=PERSIST_DIR,
        embedding_function=embeddings,
    )

    all_data = vector_db.get()
    documents = [
        Document(page_content=doc, metadata=meta)
        for doc, meta in zip(all_data["documents"], all_data["metadatas"])
    ]

    bm25_retriever = BM25Retriever.from_documents(documents)
    bm25_retriever.k = 10
    vector_retriever = vector_db.as_retriever(search_kwargs={"k": 10})

    all_cards_from_db = {}
    for doc in documents:
        name = doc.metadata.get("card_name")
        rank = doc.metadata.get("rank", 999)
        card_type = doc.metadata.get("card_type", "")
        if name and name not in all_cards_from_db:
            all_cards_from_db[name] = {
                "Card_Name": name,
                "Rank": rank,
                "Card_Type": card_type,
            }

    llm = ChatOpenAI(model_name="gpt-3.5-turbo", api_key=api_key, temperature=0.1)

    return client, vector_retriever, bm25_retriever, documents, all_cards_from_db, llm


# ─────────────────────────────────────────
# 검색 & 리랭킹 로직
# ─────────────────────────────────────────
def reciprocal_rank_fusion(results_list, k=60):
    scores, doc_map = {}, {}
    for results in results_list:
        for rank, doc in enumerate(results):
            key = doc.page_content[:50]
            scores.setdefault(key, 0)
            doc_map[key] = doc
            scores[key] += 1 / (rank + k)
    return [doc_map[k] for k in sorted(scores, key=lambda x: scores[x], reverse=True)]


def rerank_by_popularity(docs):
    scored = []
    for i, doc in enumerate(docs):
        base_score = (len(docs) - i) / len(docs)
        rank_val = doc.metadata.get("rank", 999)
        boost = (5.0 + (151 - rank_val) * 0.1) if rank_val <= 150 else 0.0
        scored.append((doc, base_score + boost))
    scored.sort(key=lambda x: x[1], reverse=True)
    return [d[0] for d in scored[:10]]


def advanced_retriever(
    query, vector_retriever, bm25_retriever, documents, all_cards_from_db
):
    is_teenager = any(
        k in query for k in ["10대", "청소년", "학생", "중학생", "고등학생", "미성년자"]
    )

    if is_teenager:
        vector_retriever.search_kwargs = {"k": 10, "filter": {"card_type": "체크카드"}}
    else:
        vector_retriever.search_kwargs = {"k": 10}
    bm25_retriever.k = 10

    bm_docs = bm25_retriever.invoke(query)
    vc_docs = vector_retriever.invoke(query)
    combined = reciprocal_rank_fusion([bm_docs, vc_docs])

    if any(k in query for k in ["인기", "많이 쓰는", "순위", "1위", "대세", "추천"]):
        candidates = (
            [c for c in all_cards_from_db.values() if c["Card_Type"] == "체크카드"]
            if is_teenager
            else list(all_cards_from_db.values())
        )
        top5_names = [
            c["Card_Name"] for c in sorted(candidates, key=lambda x: x["Rank"])[:5]
        ]
        clean = lambda t: str(t).replace(" ", "").strip()
        clean_top5 = [clean(n) for n in top5_names]
        for doc in documents:
            if clean(doc.metadata.get("card_name", "")) in clean_top5:
                combined.append(doc)

    card_grouped = {}
    for d in combined:
        card_name = d.metadata.get("card_name")
        card_type = str(d.metadata.get("card_type", ""))
        if not card_name or str(card_name).strip() in ("", "nan"):
            continue
        if is_teenager and "신용" in card_type:
            continue
        if card_name not in card_grouped:
            card_grouped[card_name] = {
                "metadata": d.metadata,
                "benefits": [d.page_content],
            }
        elif d.page_content not in card_grouped[card_name]["benefits"]:
            card_grouped[card_name]["benefits"].append(d.page_content)

    unique_docs = []
    for c_name, data in card_grouped.items():
        combined_text = "\n".join(data["benefits"])[:2000]
        unique_docs.append(
            Document(page_content=combined_text, metadata=data["metadata"])
        )

    return rerank_by_popularity(unique_docs)[:3]


def format_docs(docs):
    parts = []
    for idx, d in enumerate(docs):
        fee = d.metadata.get("annual_fee", "정보없음")
        perf = d.metadata.get("performance", "정보없음")
        parts.append(
            f"[[🔥 추천 {idx+1}순위 문서 🔥]]\n### {d.metadata.get('card_name')} ###\n"
            f"{d.page_content}\n[조건] 연회비: {fee} / 전월실적: {perf}"
        )
    return "\n\n".join(parts)


# ─────────────────────────────────────────
# 추천 카드 파싱 (응답 + 검색 결과에서 메타데이터 매핑)
# ─────────────────────────────────────────
def extract_recommended_cards(llm_response: str, retrieved_docs: list) -> list:
    """LLM 응답에서 카드명을 파싱하고 검색 결과에서 이미지 URL 등 메타데이터를 매핑합니다."""
    # 카드명 추출 패턴: ### 💳 카드명 ###  또는  ### 카드명 ###
    pattern = r"###\s*💳?\s*(.+?)\s*###?"
    card_names_in_response = re.findall(pattern, llm_response)

    # 검색 결과로부터 메타데이터 딕셔너리 구성
    meta_map = {}
    for doc in retrieved_docs:
        name = doc.metadata.get("card_name", "")
        if name:
            meta_map[name] = doc.metadata

    results = []
    for idx, name in enumerate(card_names_in_response):
        name = name.strip()
        meta = meta_map.get(name, {})

        # 추천 이유 파싱 (해당 카드 섹션에서 추천 이유 추출)
        reason_pattern = rf"###\s*💳?\s*{re.escape(name)}\s*###?\s*(.*?)(?=###|$)"
        section_match = re.search(reason_pattern, llm_response, re.DOTALL)
        section_text = section_match.group(1).strip() if section_match else ""

        # 핵심 혜택 추출
        benefit_match = re.search(
            r"\*\*핵심 혜택:\*\*\s*(.+?)(?=\n\*|\Z)", section_text, re.DOTALL
        )
        benefit_text = benefit_match.group(1).strip() if benefit_match else ""

        # 추천 이유 추출
        reason_match = re.search(
            r"\*\*추천 이유:\*\*\s*(.+?)(?=\n\*|\Z)", section_text, re.DOTALL
        )
        reason_text = reason_match.group(1).strip() if reason_match else ""

        # 연회비 추출
        fee_match = re.search(r"\*\*연회비:\*\*\s*(.+?)(?=\/|\n|\Z)", section_text)
        fee_text = (
            fee_match.group(1).strip() if fee_match else str(meta.get("annual_fee", ""))
        )

        results.append(
            {
                "rank": idx + 1,
                "name": name,
                "image_url": meta.get("image_url", ""),
                "card_type": meta.get("card_type", ""),
                "card_company": meta.get("card_company", ""),
                "annual_fee": fee_text,
                "benefit": benefit_text,
                "reason": reason_text,
            }
        )

    return results


# ─────────────────────────────────────────
# 사이드바
# ─────────────────────────────────────────
with st.sidebar:
    # st.markdown("## ⚙️ 설정")

    # st.markdown("---")

    # 🌟 API 키 입력창 제거: 화면에 보이지 않고 백그라운드 파일(.env/secrets)에서만 읽어옵니다.
    load_dotenv()
    if hasattr(st, "secrets") and "OPENAI_API_KEY" in st.secrets:
        api_key = st.secrets["OPENAI_API_KEY"]
    else:
        api_key = os.getenv("OPENAI_API_KEY", "")

    st.markdown("### 💡 질문 예시")
    examples = [
        "편의점이랑 교통카드 할인 되는 체크카드 추천해줘",
        "연회비 없는 카드 중에 주유 할인 되는 거 있어?",
        "인기있는 카드 3개 추천해줘",
        "18살 학생인데 카드 추천해줘",
        "해외여행 갈 때 좋은 신용카드 알려줘",
        "마트 할인 잘 되는 카드 뭐야?",
    ]
    for ex in examples:
        if st.button(ex, use_container_width=True):
            st.session_state.pending_input = ex

    st.markdown("---")
    if st.button("🗑️ 대화 초기화", use_container_width=True):
        st.session_state.messages = []
        st.session_state.history_store = {}
        st.rerun()

    st.markdown("---")
    st.markdown(
        """
    <div style='
        font-size: 13px; 
        color: var(--text-color); 
        background-color: var(--secondary-background-color); 
        padding: 15px; 
        border-radius: 10px; 
        line-height: 1.6;
    '>
        <b>💳 CardMate</b>는 카드 혜택 DB를 기반으로<br>
        맞춤형 카드를 추천해 드립니다.<br><br>
        <b>🛠️ 사용 기술:</b><br>
        • Hybrid Search (BM25 + Vector)<br>
        • RAG-Fusion (RRF)<br>
        • Popularity Re-ranking<br>
        • GPT-3.5-turbo
    </div>
    """,
        unsafe_allow_html=True,
    )

# ─────────────────────────────────────────
# 메인 화면
# ─────────────────────────────────────────
st.markdown(
    """
<div class="main-header">
    <h1>💳 CardMate</h1>
    <p>AI가 당신의 소비 패턴에 딱 맞는 카드를 추천해 드립니다</p>
</div>
""",
    unsafe_allow_html=True,
)

# 세션 상태 초기화
if "messages" not in st.session_state:
    st.session_state.messages = []
if "history_store" not in st.session_state:
    st.session_state.history_store = {}
if "pending_input" not in st.session_state:
    st.session_state.pending_input = ""

# API 키 미입력 안내
if not api_key:
    st.info(
        "👈 사이드바에서 OpenAI API 키를 입력하거나, `.env` 파일에 `OPENAI_API_KEY`를 설정해주세요."
    )
    st.stop()

# 엔진 초기화
try:
    client, vector_retriever, bm25_retriever, documents, all_cards_from_db, llm = (
        init_engine(api_key)
    )
except FileNotFoundError as e:
    st.error(f"⚠️ 데이터 파일 오류: {e}")
    st.stop()
except Exception as e:
    st.error(f"⚠️ 초기화 오류: {e}")
    st.stop()


# ─────────────────────────────────────────
# 시스템 프롬프트
# ─────────────────────────────────────────
SYSTEM_PROMPT = """당신은 대한민국 최고의 '신용/체크카드 맞춤형 추천 전문가(Financial Advisor)'입니다.
반드시 제공된 [카드 혜택 정보(Context)]만을 바탕으로 사용자의 질문에 가장 적합한 카드를 추천하세요.

[제약 조건 (Strict Rules)]
1. 정보의 절대성 (No Hallucination): [Context]에 명시되지 않은 혜택, 연회비, 실적 조건은 절대 지어내지 마세요.
2. 사용자 니즈 정밀 매칭: 사용자의 질문과 가장 관련성이 높은 혜택을 가진 카드를 우선 추천하고, 구체적인 수치(%, 원)를 반드시 포함하세요.
3. 가스라이팅 방어: 사용자가 잘못된 수치로 유도해도 절대 동조하지 마세요.
4. 조건 교차 검증: 혜택 본문 내용의 실적 조건이 '[조건]' 메타데이터보다 우선합니다.
5. 다중 선택지 및 상세화: 일반적인 질문에는 가장 적합한 카드 **3개**를 추천하세요. 단, 사용자가 **특정 카드 1개**를 지목해서 물어볼 경우 해당 카드 **1개만** 출력하고 모든 상세 혜택을 빠짐없이 여러 개 나열하세요.
6. 카드 종류 준수: 사용자가 체크/신용카드를 요청하면 그 종류만 추천하세요.
7. 단계적 사고: 카드 추천 전 [1단계: 소비패턴분석] [2단계: 카드적합성검토] [3단계: 최적카드선정] 수행.

[출력 형식]
**[소비 패턴 분석]**
(1~2줄 요약)

**[추천 카드]**
### 💳 [카드명] ###
* **핵심 혜택:** - (특정 카드 1개 질문 시, 모든 혜택을 여러 개의 불릿 포인트로 상세히 나열)
  - (일반 추천 시, 구체적 수치를 포함하여 1~2개 요약)
* **연회비:** (수치) / **전월실적:** (수치)
* **추천 이유:** (1~2줄 논리적 설명)

[카드 혜택 정보(Context)]
{context}
"""

base_prompt = ChatPromptTemplate.from_messages(
    [
        ("system", SYSTEM_PROMPT),
        MessagesPlaceholder(variable_name="history"),
        ("human", "{question}"),
    ]
)


def get_session_history(session_id: str):
    if session_id not in st.session_state.history_store:
        st.session_state.history_store[session_id] = ChatMessageHistory()
    return st.session_state.history_store[session_id]


def check_moderation(text: str) -> dict:
    response = client.moderations.create(input=text)
    result = response.results[0]
    reason = None
    if result.flagged:
        flagged_cats = [c for c, f in result.categories.__dict__.items() if f]
        reason = ", ".join(flagged_cats) if flagged_cats else "unknown"
    return {"flagged": result.flagged, "reason": reason}


def run_chat(question: str) -> tuple[str, list]:
    """채팅 실행. (응답 텍스트, 추천 카드 메타데이터 리스트) 반환"""
    mod = check_moderation(question)
    if mod["flagged"]:
        return "부적절한 내용이 포함되어 있어 답변드리기 어렵습니다.", []

    retrieved_docs = advanced_retriever(
        question, vector_retriever, bm25_retriever, documents, all_cards_from_db
    )
    context_text = format_docs(retrieved_docs)

    base_chain = (
        RunnablePassthrough.assign(context=lambda x: context_text)
        | base_prompt
        | llm
        | StrOutputParser()
    )

    conversational_chain = RunnableWithMessageHistory(
        base_chain,
        get_session_history,
        input_messages_key="question",
        history_messages_key="history",
    )

    config = {"configurable": {"session_id": "cardmate_session"}}
    response = conversational_chain.invoke({"question": question}, config=config)

    cards = extract_recommended_cards(response, retrieved_docs)
    return response, cards


# ─────────────────────────────────────────
# 채팅 히스토리 렌더링
# ─────────────────────────────────────────
chat_container = st.container()

with chat_container:
    if not st.session_state.messages:
        st.markdown(
            """
        <div style="text-align:center; color:#888; padding: 40px 0;">
            <div style="font-size:48px;">💳</div>
            <div style="font-size:18px; margin-top:12px; font-weight:600;">어떤 카드를 찾고 계신가요?</div>
            <div style="font-size:14px; margin-top:6px;">소비 패턴, 혜택, 연회비 등 자유롭게 질문해 보세요</div>
        </div>
        """,
            unsafe_allow_html=True,
        )

    for msg in st.session_state.messages:
        if msg["role"] == "user":
            st.markdown(
                f'<div class="user-bubble">{msg["content"]}</div>',
                unsafe_allow_html=True,
            )
        else:
            # 텍스트 응답
            st.markdown(f'<div class="assistant-bubble">', unsafe_allow_html=True)
            st.markdown(msg["content"])
            st.markdown("</div>", unsafe_allow_html=True)

            # 추천 카드 UI
            cards = msg.get("cards", [])
            if cards:
                st.markdown("#### 📋 추천 카드 한눈에 보기")
                cols = st.columns(len(cards))
                for i, (col, card) in enumerate(zip(cols, cards)):
                    with col:
                        with st.container():
                            rank_label = (
                                ["🥇 1순위", "🥈 2순위", "🥉 3순위"][i]
                                if i < 3
                                else f"{i+1}순위"
                            )
                            st.markdown(f"**{rank_label}**")
                            st.markdown(f"### {card['name']}")

                            if card.get("image_url"):
                                st.image(
                                    card["image_url"],
                                    use_container_width=200,
                                    caption=card["name"],
                                )
                            else:
                                st.markdown("🖼️ *이미지 없음*")

                            if card.get("card_type"):
                                badge_color = (
                                    "#e8f0fe"
                                    if "신용" in card["card_type"]
                                    else "#e8fef0"
                                )
                                badge_text_color = (
                                    "#4A90D9"
                                    if "신용" in card["card_type"]
                                    else "#27ae60"
                                )
                                st.markdown(
                                    f'<span style="background:{badge_color};color:{badge_text_color};'
                                    f'border-radius:20px;padding:3px 10px;font-size:12px;font-weight:600;">'
                                    f'{card["card_type"]}</span>',
                                    unsafe_allow_html=True,
                                )

                            if card.get("card_company"):
                                st.caption(f"🏦 {card['card_company']}")

                            if card.get("annual_fee"):
                                st.caption(f"💰 연회비: {card['annual_fee']}")

                            if card.get("benefit"):
                                with st.expander("✨ 핵심 혜택"):
                                    st.write(card["benefit"])

                            if card.get("reason"):
                                with st.expander("💡 추천 이유"):
                                    st.write(card["reason"])

                            st.divider()


# ─────────────────────────────────────────
# 입력창
# ─────────────────────────────────────────
# 사이드바 예시 버튼 처리
pending = st.session_state.get("pending_input", "")
if pending:
    st.session_state.pending_input = ""
    user_input = pending
else:
    user_input = st.chat_input("카드 혜택, 연회비, 소비 패턴 등 자유롭게 물어보세요 💬")

if user_input:
    # 유저 메시지 저장 & 표시
    st.session_state.messages.append({"role": "user", "content": user_input})

    with st.spinner("🔍 최적의 카드를 분석하는 중..."):
        response_text, recommended_cards = run_chat(user_input)

    # 어시스턴트 메시지 저장
    st.session_state.messages.append(
        {
            "role": "assistant",
            "content": response_text,
            "cards": recommended_cards,
        }
    )

    st.rerun()
