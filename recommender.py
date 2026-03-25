import os
import shutil
from pathlib import Path
from typing import List

from dotenv import load_dotenv
from langchain_core.documents import Document
from langchain_community.vectorstores import Chroma
from langchain_community.retrievers import BM25Retriever
from langchain_openai import OpenAIEmbeddings

from utils import (
    load_card_data,
    cards_to_semantic_documents,
    load_top_card_dict,
)

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
PERSIST_DIR = "card_semantic_db"


def get_embeddings() -> OpenAIEmbeddings:
    if not OPENAI_API_KEY:
        raise ValueError("OPENAI_API_KEY가 설정되지 않았습니다.")
    return OpenAIEmbeddings(
        api_key=OPENAI_API_KEY,
        model="text-embedding-3-small"
    )


def build_semantic_vector_db(reset: bool = False) -> Chroma:
    """
    card_data.json을 읽어 시맨틱 Chroma DB 생성
    reset=True면 기존 DB 삭제 후 재생성
    """
    if reset and Path(PERSIST_DIR).exists():
        shutil.rmtree(PERSIST_DIR)

    cards = load_card_data()
    semantic_docs = cards_to_semantic_documents(cards)
    embeddings = get_embeddings()

    vector_db = Chroma.from_documents(
        documents=semantic_docs,
        embedding=embeddings,
        persist_directory=PERSIST_DIR
    )
    return vector_db


def load_semantic_vector_db() -> Chroma:
    """
    DB가 있으면 로드, 없으면 자동 생성
    """
    embeddings = get_embeddings()

    if not Path(PERSIST_DIR).exists():
        return build_semantic_vector_db(reset=False)

    return Chroma(
        persist_directory=PERSIST_DIR,
        embedding_function=embeddings
    )


def recover_documents_from_vector_db(vector_db: Chroma) -> List[Document]:
    """
    저장된 Chroma DB에서 전체 문서를 다시 복구
    BM25 Retriever 생성용
    """
    all_data = vector_db.get()

    documents = [
        Document(page_content=doc, metadata=meta)
        for doc, meta in zip(all_data["documents"], all_data["metadatas"])
    ]
    return documents


def rerank_by_popularity(docs: List[Document]) -> List[Document]:
    """
    top_card_data.json이 있으면 인기 카드 가중치 부여
    없으면 기본 순서 유지
    """
    top_info_dict = load_top_card_dict()

    if not top_info_dict:
        return docs[:10]

    scored_docs = []
    for i, doc in enumerate(docs):
        meta = doc.metadata
        card_key = (
            meta.get("card_company"),
            meta.get("card_name"),
            meta.get("card_type"),
        )

        base_score = (len(docs) - i) / max(len(docs), 1)

        popularity_boost = 0
        top_info = top_info_dict.get(card_key)
        if top_info:
            popularity_boost = 1.5
            rank_val = top_info.get("Rank", 150)
            popularity_boost += (151 - rank_val) * 0.005

        scored_docs.append((doc, base_score + popularity_boost))

    scored_docs.sort(key=lambda x: x[1], reverse=True)
    return [d[0] for d in scored_docs[:10]]


class AdvancedHybridRetriever:
    """
    BM25 + Vector + 인기 리랭킹
    """

    def __init__(self, vector_db: Chroma):
        self.vector_db = vector_db
        self.documents = recover_documents_from_vector_db(vector_db)

        self.bm25_retriever = BM25Retriever.from_documents(self.documents)
        self.vector_retriever = vector_db.as_retriever(search_kwargs={"k": 10})

    def invoke(self, query: str) -> List[Document]:
        self.bm25_retriever.k = 10
        self.vector_retriever.search_kwargs = {"k": 10}

        bm_docs = self.bm25_retriever.invoke(query)
        vc_docs = self.vector_retriever.invoke(query)

        combined_docs = bm_docs + vc_docs

        # 카드명 기준 중복 제거
        unique_docs = []
        seen_card_names = set()

        for d in combined_docs:
            card_name = d.metadata.get("card_name")
            if card_name not in seen_card_names:
                unique_docs.append(d)
                seen_card_names.add(card_name)

        reranked_docs = rerank_by_popularity(unique_docs)
        return reranked_docs


def get_advanced_hybrid_retriever() -> AdvancedHybridRetriever:
    vector_db = load_semantic_vector_db()
    return AdvancedHybridRetriever(vector_db)


if __name__ == "__main__":
    db = build_semantic_vector_db(reset=True)
    print("시맨틱 DB 생성 완료")
    print(db._collection.count())
