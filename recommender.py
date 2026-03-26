import os
from dotenv import load_dotenv

import streamlit as st
from langchain_core.documents import Document
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_community.vectorstores import Chroma
from langchain_community.retrievers import BM25Retriever
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser
from langchain_community.chat_message_histories import ChatMessageHistory
from langchain_core.runnables.history import RunnableWithMessageHistory

from prompts import SYSTEM_PROMPT
from utils_db import ensure_vector_db

load_dotenv()

store = {}

def get_session_history(session_id: str):
    if session_id not in store:
        store[session_id] = ChatMessageHistory()
    return store[session_id]

def get_api_key():
    if "OPENAI_API_KEY" in st.secrets:
        return st.secrets["OPENAI_API_KEY"]
    return os.getenv("OPENAI_API_KEY")

@st.cache_resource(show_spinner=False)
def load_resources():
    ensure_vector_db()

    api_key = get_api_key()

    llm = ChatOpenAI(
        model_name="gpt-3.5-turbo",
        api_key=api_key,
        temperature=0
    )

    embeddings = OpenAIEmbeddings(
        api_key=api_key,
        model="text-embedding-3-small"
    )

    vector_db = Chroma(
        persist_directory="./card_semantic_db_v2",
        embedding_function=embeddings
    )

    all_data = vector_db.get()
    documents = [
        Document(page_content=doc, metadata=meta)
        for doc, meta in zip(all_data["documents"], all_data["metadatas"])
    ]

    bm25_retriever = BM25Retriever.from_documents(documents)
    vector_retriever = vector_db.as_retriever()

    all_cards_from_db = {}
    for doc in documents:
        name = doc.metadata.get("card_name")
        rank = doc.metadata.get("rank", 999)
        card_type = doc.metadata.get("card_type", "")
        if name and name not in all_cards_from_db:
            all_cards_from_db[name] = {
                "Card_Name": name,
                "Rank": rank,
                "Card_Type": card_type
            }

    return llm, vector_db, documents, bm25_retriever, vector_retriever, all_cards_from_db

def rerank_by_popularity(docs):
    scored_docs = []

    for i, doc in enumerate(docs):
        base_score = (len(docs) - i) / max(len(docs), 1)
        rank_val = doc.metadata.get("rank", 999)

        if isinstance(rank_val, int) and rank_val <= 150:
            popularity_boost = 5.0 + (151 - rank_val) * 0.1
        else:
            popularity_boost = 0.0

        scored_docs.append((doc, base_score + popularity_boost))

    scored_docs.sort(key=lambda x: x[1], reverse=True)
    return [d[0] for d in scored_docs[:10]]

def advanced_retriever_with_rerank(query: str):
    _, _, documents, bm25_retriever, vector_retriever, all_cards_from_db = load_resources()

    is_teenager = any(
        keyword in query for keyword in ["10대", "청소년", "학생", "중학생", "고등학생", "미성년자", "18살", "18세"]
    )

    if is_teenager:
        vector_retriever.search_kwargs = {"k": 10, "filter": {"card_type": "체크카드"}}
    else:
        vector_retriever.search_kwargs = {"k": 10}

    bm25_retriever.k = 10

    bm_docs = bm25_retriever.invoke(query)
    vc_docs = vector_retriever.invoke(query)
    combined_docs = bm_docs + vc_docs

    if any(keyword in query for keyword in ["인기", "많이 쓰는", "순위", "1위", "대세"]):
        if is_teenager:
            candidate_cards = [c for c in all_cards_from_db.values() if c["Card_Type"] == "체크카드"]
        else:
            candidate_cards = list(all_cards_from_db.values())

        top_5_cards = sorted(candidate_cards, key=lambda x: x["Rank"])[:5]
        top_5_names = [c["Card_Name"] for c in top_5_cards]

        for doc in documents:
            if doc.metadata.get("card_name") in top_5_names:
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
        combined_text = "\n".join(data["benefits"])
        unique_docs.append(Document(page_content=combined_text, metadata=data["metadata"]))

    return rerank_by_popularity(unique_docs)[:5]

def format_docs(docs):
    formatted = []
    for idx, d in enumerate(docs):
        fee = d.metadata.get("annual_fee", "정보없음")
        perf = d.metadata.get("performance", "정보없음")

        doc_text = (
            f"[[🔥 추천 {idx+1}순위 문서 🔥]]\n"
            f"### {d.metadata.get('card_name')} ###\n"
            f"{d.page_content}\n"
            f"[조건] 연회비: {fee} / 전월실적: {perf}"
        )
        formatted.append(doc_text)

    return "\n\n".join(formatted)

@st.cache_resource(show_spinner=False)
def build_chain():
    llm, _, _, _, _, _ = load_resources()

    base_prompt = ChatPromptTemplate.from_messages([
        ("system", SYSTEM_PROMPT),
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

    conversational_chain = RunnableWithMessageHistory(
        base_chain,
        get_session_history,
        input_messages_key="question",
        history_messages_key="history",
    )
    return conversational_chain

def ask_card_bot(question: str, session_id: str = "card_user") -> str:
    conversational_chain = build_chain()
    config = {"configurable": {"session_id": session_id}}
    return conversational_chain.invoke({"question": question}, config=config)
    
def get_recommendation_cards(question: str):
    """
    UI에 카드형으로 보여주기 위한 추천 카드 데이터 반환
    LLM 응답과 별개로 retriever 결과를 그대로 활용
    """
    docs = advanced_retriever_with_rerank(question)

    cards = []
    for d in docs[:3]:
        card = {
            "card_name": d.metadata.get("card_name", "이름 없음"),
            "annual_fee": d.metadata.get("annual_fee", "정보없음"),
            "performance": d.metadata.get("performance", "정보없음"),
            "image_url": d.metadata.get("image_url") or d.metadata.get("Image_URL", ""),
            "benefit_summary": (d.page_content[:180] + "...") if len(d.page_content) > 180 else d.page_content
        }
        cards.append(card)

    return cards
