# recommender.py
# =========================================================
# [이 파일의 역할]
# - Vector DB 로드
# - BM25 + Vector 하이브리드 검색
# - 인기 카드 리랭킹
# - 카드 이미지 URL 포함한 카드 데이터 반환
# =========================================================

import os
from dotenv import load_dotenv

from langchain_core.documents import Document
from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import Chroma
from langchain_community.retrievers import BM25Retriever

from utils_db import ensure_vector_db

load_dotenv()


def get_api_key() -> str:
    """
    Streamlit secrets 또는 .env에서 OpenAI API Key를 읽어옵니다.
    """
    try:
        import streamlit as st
        if "OPENAI_API_KEY" in st.secrets:
            return st.secrets["OPENAI_API_KEY"]
    except Exception:
        pass

    return os.getenv("OPENAI_API_KEY", "")


# =========================================================
# [DB / Retriever 준비]
# - 앱 시작 시 1회 로드
# =========================================================
DB_READY = False
vector_db = None
documents = None
bm25_retriever = None
vector_retriever = None
all_cards_from_db = None


def initialize_recommender():
    """
    Vector DB 및 Retriever를 한 번만 초기화합니다.
    """
    global DB_READY, vector_db, documents, bm25_retriever, vector_retriever, all_cards_from_db

    if DB_READY:
        return

    ensure_vector_db()

    embeddings = OpenAIEmbeddings(
        api_key=get_api_key(),
        model="text-embedding-3-small"
    )

    vector_db = Chroma(
        persist_directory="./card_semantic_db_v3",
        embedding_function=embeddings
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

    DB_READY = True


# =========================================================
# [이미지 URL 추출]
# - metadata에 저장된 카드 이미지 URL을 찾습니다.
# =========================================================
def get_image_url(metadata: dict) -> str:
    for key in ["image_url", "Image_URL", "img_url", "card_image_url", "image"]:
        value = metadata.get(key)
        if value and str(value).strip():
            return str(value).strip()
    return ""


def summarize_benefit(text: str, max_len: int = 180) -> str:
    """
    카드 UI에 보여줄 짧은 혜택 요약문
    """
    if not text:
        return "혜택 정보 없음"
    text = text.strip().replace("\n", " ")
    return text[:max_len] + "..." if len(text) > max_len else text


# =========================================================
# [인기순 리랭킹]
# - rank 메타데이터 기반 가중치 부여
# =========================================================
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


# =========================================================
# [하이브리드 검색 + 인기카드 주입 + 혜택 병합]
# =========================================================
def advanced_retriever_with_rerank(query: str):
    initialize_recommender()

    is_teenager = any(
        keyword in query
        for keyword in ["10대", "청소년", "학생", "중학생", "고등학생", "미성년자"]
    )

    # 1) retriever 세팅
    if is_teenager:
        vector_retriever.search_kwargs = {"k": 10, "filter": {"card_type": "체크카드"}}
    else:
        vector_retriever.search_kwargs = {"k": 10}
    bm25_retriever.k = 10

    # 2) 하이브리드 검색
    bm_docs = bm25_retriever.invoke(query)
    vc_docs = vector_retriever.invoke(query)
    combined_docs = bm_docs + vc_docs

    # 3) 인기 카드 강제 주입
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

    # 4) 카드별 혜택 병합
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
        unique_docs.append(Document(page_content=combined_text, metadata=data["metadata"]))

    return rerank_by_popularity(unique_docs)[:3]


# =========================================================
# [LLM Context용 문자열 생성]
# - 이미지 URL도 같이 넣어서 LLM이 답변에 활용 가능
# =========================================================
def format_docs(docs):
    formatted = []

    for idx, d in enumerate(docs):
        fee = d.metadata.get("annual_fee", "정보없음")
        perf = d.metadata.get("performance", "정보없음")
        image_url = get_image_url(d.metadata)
        benefit_text = d.page_content[:300]

        doc_text = (
            f"[[🔥 추천 {idx+1}순위 문서 🔥]]\n"
            f"[카드명] {d.metadata.get('card_name')}\n"
            f"[혜택] {benefit_text}\n"
            f"[연회비] {fee}\n"
            f"[전월실적] {perf}\n"
            f"[이미지URL] {image_url}"
        )
        formatted.append(doc_text)

    return "\n\n".join(formatted)


# =========================================================
# [Streamlit 카드 UI용 데이터]
# - app.py에서 카드 이미지와 함께 렌더링할 때 사용
# =========================================================
def get_recommendation_cards(question: str):
    docs = advanced_retriever_with_rerank(question)
    cards = []

    for d in docs[:3]:
        cards.append({
            "card_name": d.metadata.get("card_name", "이름 없음"),
            "annual_fee": d.metadata.get("annual_fee", "정보없음"),
            "performance": d.metadata.get("performance", "정보없음"),
            "image_url": get_image_url(d.metadata),
            "benefit_summary": summarize_benefit(d.page_content, 180),
        })

    return cards
