from pathlib import Path
import shutil
from typing import List

from langchain_core.documents import Document
from langchain_community.vectorstores import Chroma
from langchain_community.retrievers import BM25Retriever
from langchain_openai import OpenAIEmbeddings

from utils import load_card_data, cards_to_semantic_documents, load_top_card_dict

PERSIST_DIR = "card_semantic_db"


def get_embeddings(openai_api_key: str) -> OpenAIEmbeddings:
    if not openai_api_key:
        raise ValueError("OpenAI API 키가 없습니다.")
    return OpenAIEmbeddings(
        api_key=openai_api_key,
        model="text-embedding-3-small"
    )


def build_semantic_vector_db(openai_api_key: str, reset: bool = False) -> Chroma:
    if reset and Path(PERSIST_DIR).exists():
        shutil.rmtree(PERSIST_DIR)

    cards = load_card_data()
    semantic_docs = cards_to_semantic_documents(cards)
    embeddings = get_embeddings(openai_api_key)

    vector_db = Chroma.from_documents(
        documents=semantic_docs,
        embedding=embeddings,
        persist_directory=PERSIST_DIR
    )
    return vector_db


def load_semantic_vector_db(openai_api_key: str) -> Chroma:
    embeddings = get_embeddings(openai_api_key)

    if not Path(PERSIST_DIR).exists():
        return build_semantic_vector_db(openai_api_key=openai_api_key, reset=False)

    return Chroma(
        persist_directory=PERSIST_DIR,
        embedding_function=embeddings
    )


def recover_documents_from_vector_db(vector_db: Chroma) -> List[Document]:
    all_data = vector_db.get()

    docs = all_data.get("documents", [])
    metas = all_data.get("metadatas", [])

    if not docs or not metas:
        return []

    documents = []
    for doc, meta in zip(docs, metas):
        if doc is None:
            continue
        documents.append(Document(page_content=doc, metadata=meta or {}))

    return documents


def rerank_by_popularity(docs: List[Document]) -> List[Document]:
    top_info_dict = load_top_card_dict()

    if not top_info_dict:
        return docs[:10]

    scored_docs = []
    for i, doc in enumerate(docs):
        meta = doc.metadata
        card_key = (
            str(meta.get("card_company", "")).lower(),
            str(meta.get("card_name", "")).lower(),
            str(meta.get("card_type", "")).lower(),
        )

        base_score = (len(docs) - i) / max(len(docs), 1)

        top_info = top_info_dict.get(card_key)
        if top_info:
            rank_val = top_info.get("Rank", 150)
            popularity_boost = 5.0 + (151 - rank_val) * 0.1
        else:
            popularity_boost = 0.0

        scored_docs.append((doc, base_score + popularity_boost))

    scored_docs.sort(key=lambda x: x[1], reverse=True)
    return [d[0] for d in scored_docs[:10]]


class AdvancedHybridRetriever:
    def __init__(self, vector_db: Chroma):
        self.vector_db = vector_db
        self.documents = recover_documents_from_vector_db(vector_db)

        self.bm25_retriever = BM25Retriever.from_documents(self.documents) if self.documents else None
        self.vector_retriever = vector_db.as_retriever(search_kwargs={"k": 10})

    def invoke(self, query: str) -> List[Document]:
        vector_docs = self.vector_retriever.invoke(query)

        bm_docs = []
        if self.bm25_retriever is not None:
            self.bm25_retriever.k = 10
            bm_docs = self.bm25_retriever.invoke(query)

        combined_docs = bm_docs + vector_docs

        unique_docs = []
        seen_keys = set()

        for d in combined_docs:
            key = (
                d.metadata.get("card_company", ""),
                d.metadata.get("card_name", ""),
                d.metadata.get("card_type", "")
            )
            if key not in seen_keys:
                unique_docs.append(d)
                seen_keys.add(key)

        top_info_dict = load_top_card_dict()
        if top_info_dict and any(keyword in query for keyword in ["인기", "많이 쓰는", "순위", "1위", "추천"]):
            top_5_cards = sorted(top_info_dict.values(), key=lambda x: x.get("Rank", 999))[:5]
            for card_info in top_5_cards:
                target_name = str(card_info.get("Card_Name", "")).lower()
                for doc in self.documents:
                    if str(doc.metadata.get("card_name", "")).lower() == target_name:
                        key = (
                            doc.metadata.get("card_company", ""),
                            doc.metadata.get("card_name", ""),
                            doc.metadata.get("card_type", "")
                        )
                        if key not in seen_keys:
                            unique_docs.append(doc)
                            seen_keys.add(key)
                        break

        return rerank_by_popularity(unique_docs)


def get_advanced_hybrid_retriever(openai_api_key: str) -> AdvancedHybridRetriever:
    vector_db = load_semantic_vector_db(openai_api_key)
    return AdvancedHybridRetriever(vector_db)
