import os
from pathlib import Path

from dotenv import load_dotenv
from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import Chroma

from utils import load_card_data, cards_to_documents

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
PERSIST_DIR = "chroma_db"


def get_embeddings() -> OpenAIEmbeddings:
    if not OPENAI_API_KEY:
        raise ValueError("OPENAI_API_KEY가 설정되지 않았습니다.")

    return OpenAIEmbeddings(
        api_key=OPENAI_API_KEY,
        model="text-embedding-3-small"
    )


def build_vector_db() -> Chroma:
    cards = load_card_data()
    docs = cards_to_documents(cards)
    embeddings = get_embeddings()

    vectordb = Chroma.from_documents(
        documents=docs,
        embedding=embeddings,
        persist_directory=PERSIST_DIR
    )
    return vectordb


def load_vector_db() -> Chroma:
    embeddings = get_embeddings()

    if not Path(PERSIST_DIR).exists():
        return build_vector_db()

    return Chroma(
        persist_directory=PERSIST_DIR,
        embedding_function=embeddings
    )


if __name__ == "__main__":
    db = build_vector_db()
    print("벡터 DB 생성 완료")
    print(db._collection.count())
