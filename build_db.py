# utils_db.py
import os
import shutil
import zipfile
from pathlib import Path

import gdown
import streamlit as st
from langchain_core.documents import Document
from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import Chroma
from langchain_community.retrievers import BM25Retriever


DB_ZIP_PATH = Path("./card_semantic_db_v3.zip")
DB_EXTRACT_ROOT = Path("./db_cache")
DB_DIR = DB_EXTRACT_ROOT / "card_semantic_db_v3"


def download_and_prepare_db(file_id: str) -> str:
    """
    구글드라이브에서 card_semantic_db_v3.zip 다운로드 후 압축 해제.
    반환값: 실제 Chroma persist_directory 경로
    """
    DB_EXTRACT_ROOT.mkdir(parents=True, exist_ok=True)

    # 이미 압축 해제된 폴더가 있으면 재사용
    if DB_DIR.exists() and any(DB_DIR.iterdir()):
        return str(DB_DIR)

    # 기존 zip 제거
    if DB_ZIP_PATH.exists():
        DB_ZIP_PATH.unlink()

    url = f"https://drive.google.com/uc?id={file_id}"
    gdown.download(url, str(DB_ZIP_PATH), quiet=False)

    if not DB_ZIP_PATH.exists():
        raise FileNotFoundError("DB zip 다운로드 실패")

    # 기존 압축 폴더 초기화
    if DB_EXTRACT_ROOT.exists():
        shutil.rmtree(DB_EXTRACT_ROOT)
    DB_EXTRACT_ROOT.mkdir(parents=True, exist_ok=True)

    # 압축 해제
    with zipfile.ZipFile(DB_ZIP_PATH, "r") as zip_ref:
        zip_ref.extractall(DB_EXTRACT_ROOT)

    # 1) 정상 구조: db_cache/card_semantic_db_v3/
    if DB_DIR.exists() and any(DB_DIR.iterdir()):
        return str(DB_DIR)

    extracted_items = list(DB_EXTRACT_ROOT.iterdir())

    # 2) zip 내부에 파일들이 바로 있는 경우
    if extracted_items and any(item.is_file() for item in extracted_items):
        DB_DIR.mkdir(parents=True, exist_ok=True)
        for item in extracted_items:
            if item.name != "card_semantic_db_v3":
                shutil.move(str(item), str(DB_DIR / item.name))
        return str(DB_DIR)

    # 3) zip 내부에 폴더 하나만 있고 그게 실제 DB 폴더인 경우
    if len(extracted_items) == 1 and extracted_items[0].is_dir():
        return str(extracted_items[0])

    raise FileNotFoundError("압축 해제 후 Chroma DB 폴더를 찾지 못했습니다.")


@st.cache_resource(show_spinner=True)
def load_rag_resources(openai_api_key: str, gdrive_db_file_id: str):
    """
    구글드라이브 zip → 압축 해제 → Chroma 로드 → BM25/Vector Retriever 생성
    """
    db_path = download_and_prepare_db(gdrive_db_file_id)

    embeddings = OpenAIEmbeddings(
        api_key=openai_api_key,
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

    return {
        "db_path": db_path,
        "vector_db": vector_db,
        "documents": documents,
        "bm25_retriever": bm25_retriever,
        "vector_retriever": vector_retriever,
        "all_cards_from_db": all_cards_from_db,
    }
