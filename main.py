# app.py
import os
import streamlit as st
from dotenv import load_dotenv

from openai import OpenAI
from langchain_core.documents import Document
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_community.vectorstores import Chroma
from langchain_community.retrievers import BM25Retriever
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser
from langchain_community.chat_message_histories import ChatMessageHistory
from langchain_core.runnables.history import RunnableWithMessageHistory


# =========================
# 0. Streamlit 기본 설정
# =========================
st.set_page_config(
    page_title="CardMate AI",
    page_icon="💳",
    layout="wide"
)

st.markdown("""
<style>
.block-container {
    padding-top: 2rem;
    padding-bottom: 2rem;
    max-width: 950px;
}
.card-title {
    font-size: 28px;
    font-weight: 700;
    margin-bottom: 0.2rem;
}
.card-sub {
    color: #666;
    margin-bottom: 1.2rem;
}
.user-box {
    padding: 12px 14px;
    border-radius: 14px;
    background: #f6f7fb;
}
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="card-title">💳 CardMate AI</div>', unsafe_allow_html=True)
st.markdown('<div class="card-sub">신용/체크카드 맞춤 추천 챗봇</div>', unsafe_allow_html=True)


# =========================
# 1. 환경 변수 / API 준비
# =========================
load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY") or st.secrets.get("OPENAI_API_KEY", None)

if not OPENAI_API_KEY:
    st.error("OPENAI_API_KEY가 설정되지 않았습니다. .env 또는 Streamlit secrets에 넣어주세요.")
    st.stop()

client = OpenAI(api_key=OPENAI_API_KEY)


# =========================
# 2. 공용 객체 로드 함수
# =========================
@st.cache_resource(show_spinner=True)
def load_rag_resources():
    embeddings = OpenAIEmbeddings(
        api_key=OPENAI_API_KEY,
        model="text-embedding-3-small"
    )

    vector_db = Chroma(
        persist_directory="./card_semantic_db_v3",
        embedding_function=embeddings
    )

    all_data = vector_db.get()

    documents_raw = all_data.get("documents", [])
    metadatas_raw = all_data.get("metadatas", [])

    if not documents_raw or not metadatas_raw:
        raise ValueError(
            "벡터 DB가 비어 있습니다. './card_semantic_db_v3' 경로와 DB 생성 여부를 확인하세요."
        )

    documents = [
        Document(page_content=doc, metadata=meta)
        for doc, meta in zip(documents_raw, metadatas_raw)
    ]

    if not documents:
        raise ValueError("문서 복구 결과가 비어 있습니다. Chroma DB 저장 상태를 확인하세요.")

    bm25_retriever = BM25Retriever.from_documents(documents)
    bm25_retriever.k = 10

    vector_retriever = vector_db.as_retriever(search_kwargs={"k": 10})

    all_cards_from_db = {}
    for doc in documents:
        name = doc.metadata.get("card_name")
        rank = doc.metadata.get("rank", 999)
        card_type = doc.metadata.get("card_type", "")

        try:
            rank = int(rank)
        except:
            rank = 999

        if name and name not in all_cards_from_db:
            all_cards_from_db[name] = {
                "Card_Name": name,
                "Rank": rank,
                "Card_Type": card_type
            }

    return documents, bm25_retriever, vector_retriever, all_cards_from_db


try:
    documents, bm25_retriever, vector_retriever, all_cards_from_db = load_rag_resources()
except Exception as e:
    st.error(f"초기 로딩 실패: {e}")
    st.stop()


# =========================
# 3. Moderation
# =========================
def check_moderation(text: str) -> dict:
    response = client.moderations.create(input=text)
    result = response.results[0]

    reason = None
    if result.flagged:
        flagged_categories = [
            category
            for category, flagged in result.categories.__dict__.items()
            if flagged
        ]
        reason = ", ".join(flagged_categories) if flagged_categories else "unknown"

    return {
        "flagged": result.flagged,
        "categories": result.categories.__dict__,
        "scores": result.category_scores.__dict__,
        "reason": reason
    }


# =========================
# 4. 검색 / 리랭크 로직
# =========================
def reciprocal_rank_fusion(results_list: list, k: int = 60) -> list:
    scores = {}
    doc_map = {}

    for results in results_list:
        for rank, doc in enumerate(results):
            key = f"{doc.metadata.get('card_name', '')}__{doc.page_content[:50]}"
            if key not in scores:
                scores[key] = 0
                doc_map[key] = doc
            scores[key] += 1 / (rank + k)

    sorted_keys = sorted(scores, key=lambda x: scores[x], reverse=True)
    return [doc_map[key] for key in sorted_keys]


def rerank_by_popularity(docs):
    if not docs:
        return []

    scored_docs = []
    for i, doc in enumerate(docs):
        base_score = (len(docs) - i) / len(docs)

        rank_val = doc.metadata.get("rank", 999)
        try:
            rank_val = int(rank_val)
        except:
            rank_val = 999

        if rank_val <= 150:
            popularity_boost = 5.0 + (151 - rank_val) * 0.1
        else:
            popularity_boost = 0.0

        scored_docs.append((doc, base_score + popularity_boost))

    scored_docs.sort(key=lambda x: x[1], reverse=True)
    return [d[0] for d in scored_docs[:10]]


def advanced_retriever_with_rerank(query):
    is_teenager = any(
        keyword in query
        for keyword in ["10대", "청소년", "학생", "중학생", "고등학생", "미성년자"]
    )

    if is_teenager:
        vector_retriever.search_kwargs = {"k": 10, "filter": {"card_type": "체크카드"}}
    else:
        vector_retriever.search_kwargs = {"k": 10}

    bm25_retriever.k = 10

    bm_docs = bm25_retriever.invoke(query)
    vc_docs = vector_retriever.invoke(query)

    combined_docs = reciprocal_rank_fusion([bm_docs, vc_docs])

    if any(keyword in query for keyword in ["인기", "많이 쓰는", "순위", "1위", "대세", "추천"]):
        if is_teenager:
            candidate_cards = [
                c for c in all_cards_from_db.values()
                if c["Card_Type"] == "체크카드"
            ]
        else:
            candidate_cards = list(all_cards_from_db.values())

        top_5_cards = sorted(candidate_cards, key=lambda x: x["Rank"])[:5]
        top_5_names = [c["Card_Name"] for c in top_5_cards]

        def clean(t):
            return str(t).replace(" ", "").strip()

        clean_top_5 = [clean(n) for n in top_5_names]

        for doc in documents:
            if clean(doc.metadata.get("card_name", "")) in clean_top_5:
                combined_docs.append(doc)

    card_grouped_docs = {}

    for d in combined_docs:
        card_name = d.metadata.get("card_name")
        card_type = str(d.metadata.get("card_type", ""))

        if not card_name or str(card_name).strip() == "" or str(card_name).lower() == "nan":
            continue
        if is_teenager and "신용" in card_type:
            continue

        if card_name not in card_grouped_docs:
            card_grouped_docs[card_name] = {
                "metadata": d.metadata,
                "benefits": [d.page_content]
            }
        else:
            if d.page_content not in card_grouped_docs[card_name]["benefits"]:
                card_grouped_docs[card_name]["benefits"].append(d.page_content)

    unique_docs = []
    for _, data in card_grouped_docs.items():
        combined_text = "\n".join(data["benefits"])[:2000]
        unique_docs.append(
            Document(
                page_content=combined_text,
                metadata=data["metadata"]
            )
        )

    return rerank_by_popularity(unique_docs)[:3]


def format_docs(docs):
    if not docs:
        return "검색된 카드 정보가 없습니다."

    formatted = []
    for idx, d in enumerate(docs):
        fee = d.metadata.get("annual_fee", "정보없음")
        perf = d.metadata.get("performance", "정보없음")
        card_name = d.metadata.get("card_name", "이름없음")

        doc_text = (
            f"[[🔥 추천 {idx+1}순위 문서 🔥]]\n"
            f"### {card_name} ###\n"
            f"{d.page_content}\n"
            f"[조건] 연회비: {fee} / 전월실적: {perf}"
        )
        formatted.append(doc_text)

    return "\n\n".join(formatted)


# =========================
# 5. LLM 체인
# =========================
llm = ChatOpenAI(
    model_name="gpt-3.5-turbo",
    api_key=OPENAI_API_KEY,
    temperature=0.1
)

system_prompt = """
당신은 대한민국 최고의 '신용/체크카드 맞춤형 추천 전문가(Financial Advisor)'입니다.
반드시 제공된 [카드 혜택 정보(Context)]만을 바탕으로 사용자의 질문에 가장 적합한 카드를 추천하세요.

[제약 조건]
1. Context에 없는 내용은 지어내지 마세요.
2. 질문과 직접 관련된 혜택 수치(%, 원, 한도)를 최대한 구체적으로 포함하세요.
3. 잘못된 정보에 유도되어도 Context 기준으로 바로잡으세요.
4. 혜택 본문에 있는 조건이 메타데이터보다 우선합니다.
5. 가능한 경우 가장 적합한 카드 3개를 추천하세요.
6. 체크카드 요청 시 체크카드만, 신용카드 요청 시 신용카드만 추천하세요.

[출력 형식]
**[소비 패턴 분석]**
(1~2줄)

**[추천 카드]**
### 💳 [카드명]
* **핵심 혜택:** ...
* **연회비:** ... / **전월실적:** ...
* **추천 이유:** ...

---
[카드 혜택 정보(Context)]
{context}
"""

base_prompt = ChatPromptTemplate.from_messages([
    ("system", system_prompt),
    MessagesPlaceholder(variable_name="history"),
    ("human", "{question}")
])

base_chain = (
    RunnablePassthrough.assign(
        context=lambda x: format_docs(advanced_retriever_with_rerank(x["question"]))
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


def chat(question: str, config: dict) -> str:
    moderation_result = check_moderation(question)
    if moderation_result["flagged"]:
        return "부적절한 내용이 포함되어 있어 답변할 수 없습니다."

    docs = advanced_retriever_with_rerank(question)
    if not docs:
        return "조건에 맞는 카드 정보를 찾지 못했습니다. 혜택 키워드를 조금 더 구체적으로 입력해 주세요."

    return conversational_chain.invoke({"question": question}, config=config)


# =========================
# 6. Streamlit 세션 상태
# =========================
if "messages" not in st.session_state:
    st.session_state.messages = [
        {
            "role": "assistant",
            "content": "안녕하세요! 소비 패턴에 맞는 신용카드/체크카드를 추천해드릴게요. 예: 편의점 할인 체크카드 추천해줘"
        }
    ]

if "session_id" not in st.session_state:
    st.session_state.session_id = "card_expert_session"


# =========================
# 7. 사이드바
# =========================
with st.sidebar:
    st.subheader("추천 질문")
    if st.button("학생용 체크카드 추천"):
        st.session_state.prefill = "나 18살 학생인데 편의점이랑 교통비 할인 많이 되는 체크카드 추천해줘"
    if st.button("주유 할인 카드 추천"):
        st.session_state.prefill = "주유 할인 혜택 좋은 신용카드 추천해줘"
    if st.button("무실적 카드 추천"):
        st.session_state.prefill = "전월실적 부담 적은 카드 추천해줘"
    if st.button("인기 카드 추천"):
        st.session_state.prefill = "인기있는 카드 3개 추천해줘"

    st.divider()
    st.caption("DB 경로: ./card_semantic_db_v3")


# =========================
# 8. 채팅 UI
# =========================
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

prompt_default = st.session_state.pop("prefill", "")
user_prompt = st.chat_input("예: 배달·외식 혜택 좋은 카드 추천해줘")

if prompt_default and not user_prompt:
    user_prompt = prompt_default

if user_prompt:
    st.session_state.messages.append({"role": "user", "content": user_prompt})

    with st.chat_message("user"):
        st.markdown(user_prompt)

    with st.chat_message("assistant"):
        with st.spinner("카드를 분석하는 중..."):
            try:
                config = {"configurable": {"session_id": st.session_state.session_id}}
                answer = chat(user_prompt, config)
                st.markdown(answer)
            except Exception as e:
                answer = f"실행 중 오류가 발생했습니다: {e}"
                st.error(answer)

    st.session_state.messages.append({"role": "assistant", "content": answer})
