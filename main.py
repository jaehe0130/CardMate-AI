import os
import shutil
import zipfile
from pathlib import Path

import gdown
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
st.set_page_config(page_title="CardMate AI", page_icon="💳", layout="wide")

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY") or st.secrets.get("OPENAI_API_KEY", None)
GDRIVE_DB_FILE_ID = os.getenv("GDRIVE_DB_FILE_ID") or st.secrets.get("GDRIVE_DB_FILE_ID", None)

if not OPENAI_API_KEY:
    st.error("OPENAI_API_KEY가 없습니다.")
    st.stop()

if not GDRIVE_DB_FILE_ID:
    st.error("GDRIVE_DB_FILE_ID가 없습니다.")
    st.stop()

client = OpenAI(api_key=OPENAI_API_KEY)


# =========================
# 1. 구글드라이브 zip 다운로드/압축해제
# =========================
DB_ZIP_PATH = Path("./card_semantic_db_v3.zip")
DB_EXTRACT_ROOT = Path("./db_cache")
DB_DIR = DB_EXTRACT_ROOT / "card_semantic_db_v3"


def download_and_prepare_db(file_id: str):
    """
    구글드라이브에서 zip 다운로드 후 압축 해제.
    압축 결과로 ./db_cache/card_semantic_db_v3 가 생성되도록 처리.
    """
    DB_EXTRACT_ROOT.mkdir(parents=True, exist_ok=True)

    # 이미 압축 해제된 DB 폴더가 있으면 재사용
    if DB_DIR.exists() and any(DB_DIR.iterdir()):
        return str(DB_DIR)

    # 기존 zip 파일 삭제 후 새로 다운로드
    if DB_ZIP_PATH.exists():
        DB_ZIP_PATH.unlink()

    url = f"https://drive.google.com/uc?id={file_id}"
    gdown.download(url, str(DB_ZIP_PATH), quiet=False)

    if not DB_ZIP_PATH.exists():
        raise FileNotFoundError("DB zip 다운로드 실패")

    # 기존 압축 해제 폴더 정리
    if DB_EXTRACT_ROOT.exists():
        shutil.rmtree(DB_EXTRACT_ROOT)
    DB_EXTRACT_ROOT.mkdir(parents=True, exist_ok=True)

    # 압축 해제
    with zipfile.ZipFile(DB_ZIP_PATH, "r") as zip_ref:
        zip_ref.extractall(DB_EXTRACT_ROOT)

    # zip 안에 card_semantic_db_v3 폴더가 있는 경우
    if DB_DIR.exists() and any(DB_DIR.iterdir()):
        return str(DB_DIR)

    # zip 안에 바로 chroma 파일들이 풀린 경우 대응
    extracted_items = list(DB_EXTRACT_ROOT.iterdir())
    if extracted_items:
        # card_semantic_db_v3 폴더가 없고 파일들이 바로 풀렸으면 폴더로 이동
        if any(item.is_file() for item in extracted_items):
            DB_DIR.mkdir(parents=True, exist_ok=True)
            for item in extracted_items:
                if item.name != "card_semantic_db_v3":
                    shutil.move(str(item), str(DB_DIR / item.name))
            return str(DB_DIR)

        # 하위 폴더 하나만 있고 그게 실제 DB 폴더인 경우
        if len(extracted_items) == 1 and extracted_items[0].is_dir():
            return str(extracted_items[0])

    raise FileNotFoundError("압축 해제 후 Chroma DB 폴더를 찾지 못했습니다.")


# =========================
# 2. 리소스 로드
# =========================
@st.cache_resource(show_spinner=True)
def load_rag_resources():
    db_path = download_and_prepare_db(GDRIVE_DB_FILE_ID)

    embeddings = OpenAIEmbeddings(
        api_key=OPENAI_API_KEY,
        model="text-embedding-3-small"
    )

    vector_db = Chroma(
        persist_directory=db_path,
        embedding_function=embeddings
    )

    all_data = vector_db.get()
    documents_raw = all_data.get("documents", [])
    metadatas_raw = all_data.get("metadatas", [])

    if not documents_raw or not metadatas_raw:
        raise ValueError("벡터 DB가 비어 있습니다. zip 내용 확인 필요")

    documents = [
        Document(page_content=doc, metadata=meta)
        for doc, meta in zip(documents_raw, metadatas_raw)
    ]

    if not documents:
        raise ValueError("문서 복구 결과가 비어 있습니다.")

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

    return db_path, documents, bm25_retriever, vector_retriever, all_cards_from_db


try:
    db_path, documents, bm25_retriever, vector_retriever, all_cards_from_db = load_rag_resources()
    st.success(f"DB 로드 완료: {db_path}")
except Exception as e:
    st.error(f"DB 로드 실패: {e}")
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
        "reason": reason
    }


# =========================
# 4. 검색 / 리랭크
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

        popularity_boost = 5.0 + (151 - rank_val) * 0.1 if rank_val <= 150 else 0.0
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
            candidate_cards = [c for c in all_cards_from_db.values() if c["Card_Type"] == "체크카드"]
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
            card_grouped_docs[card_name] = {"metadata": d.metadata, "benefits": [d.page_content]}
        else:
            if d.page_content not in card_grouped_docs[card_name]["benefits"]:
                card_grouped_docs[card_name]["benefits"].append(d.page_content)

    unique_docs = []
    for _, data in card_grouped_docs.items():
        combined_text = "\n".join(data["benefits"])[:2000]
        unique_docs.append(Document(page_content=combined_text, metadata=data["metadata"]))

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
# 5. 체인
# =========================
llm = ChatOpenAI(
    model_name="gpt-3.5-turbo",
    api_key=OPENAI_API_KEY,
    temperature=0.1
)

system_prompt = """
당신은 대한민국 최고의 신용/체크카드 맞춤형 추천 전문가입니다.
반드시 제공된 카드 혜택 정보(Context)만을 바탕으로 사용자의 질문에 답하세요.

[규칙]
1. Context 밖 정보는 만들지 마세요.
2. 질문과 직접 관련된 혜택 수치(%, 원, 한도)를 포함하세요.
3. 가능한 경우 카드 3개를 추천하세요.
4. 체크카드 요청 시 체크카드만, 신용카드 요청 시 신용카드만 추천하세요.

[출력 형식]
**[소비 패턴 분석]**
...

**[추천 카드]**
### 💳 카드명
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
# 6. UI
# =========================
st.title("💳 CardMate AI")
st.caption("구글드라이브의 card_semantic_db_v3.zip을 내려받아 카드 추천 DB로 사용합니다.")

if "messages" not in st.session_state:
    st.session_state.messages = [
        {
            "role": "assistant",
            "content": "안녕하세요! 원하는 소비 패턴을 말씀해 주세요. 예: 편의점 할인 체크카드 추천해줘"
        }
    ]

if "session_id" not in st.session_state:
    st.session_state.session_id = "card_expert_session"

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

user_prompt = st.chat_input("예: 나 18살 학생인데 편의점/교통 할인 체크카드 추천해줘")

if user_prompt:
    st.session_state.messages.append({"role": "user", "content": user_prompt})
    with st.chat_message("user"):
        st.markdown(user_prompt)

    with st.chat_message("assistant"):
        with st.spinner("카드 분석 중..."):
            try:
                config = {"configurable": {"session_id": st.session_state.session_id}}
                answer = chat(user_prompt, config)
                st.markdown(answer)
            except Exception as e:
                answer = f"오류가 발생했습니다: {e}"
                st.error(answer)

    st.session_state.messages.append({"role": "assistant", "content": answer})
