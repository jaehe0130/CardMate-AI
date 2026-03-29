"""
build_db.py
───────────
card_semantic_db_v3 폴더(Chroma DB)를 merged_card_data.json으로부터 새로 빌드합니다.

사용법:
    python build_db.py

환경변수:
    OPENAI_API_KEY  (또는 .env 파일)

주의:
    - 기존 card_semantic_db_v3 폴더가 있으면 삭제 후 재생성합니다.
    - OpenAI Embedding API를 호출하므로 소정의 비용이 발생합니다.
    - 완료 후 card_semantic_db_v3/ 폴더를 .gitignore에 추가하세요.
"""

import os
import json
import shutil

from dotenv import load_dotenv
from langchain_core.documents import Document
from langchain_openai import OpenAIEmbeddings
from langchain_chroma import Chroma

# ─────────────────────────────────────────
# 설정
# ─────────────────────────────────────────
PERSIST_DIR   = "./card_semantic_db_v3"
DATA_FILE     = "./merged_card_data.json"
EMBED_MODEL   = "text-embedding-3-small"
MAX_BENEFIT_LEN = 350   # 혜택 1개당 최대 글자수 (노트북과 동일)


def load_api_key() -> str:
    load_dotenv()
    key = os.getenv("OPENAI_API_KEY", "")
    if not key:
        raise EnvironmentError(
            "OPENAI_API_KEY가 설정되지 않았습니다.\n"
            ".env 파일에 OPENAI_API_KEY=sk-... 를 추가하거나 환경변수로 설정해 주세요."
        )
    return key


def load_card_data(path: str) -> list:
    if not os.path.exists(path):
        raise FileNotFoundError(f"데이터 파일을 찾을 수 없습니다: {path}")
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    print(f"📂 카드 데이터 로드 완료: {len(data)}개 카드")
    return data


def build_semantic_docs(card_data: list) -> list[Document]:
    """노트북과 동일한 시맨틱 청킹 로직 (1 혜택 = 1 Document)"""
    semantic_docs = []

    for card in card_data:
        card_name = card.get("Card_Name", "이름 없음")
        card_type = card.get("Card_Type", "구분 없음")
        company   = card.get("Card_Company", "카드사 없음")
        perf      = card.get("Base_Perf_Num", 0)
        fee_dom   = card.get("Annual_Fee_Domestic", 0)
        fee_ovs   = card.get("Annual_Fee_Overseas", 0)
        image_url = card.get("Image_URL", "")
        rank      = int(card.get("Rank", 999))
        benefits  = card.get("Benefits_Summary", [])

        base_meta = {
            "card_name"    : card_name,
            "card_company" : company,
            "card_type"    : card_type,
            "performance"  : perf,
            "annual_fee"   : fee_dom,
            "image_url"    : image_url,
            "rank"         : rank,
        }

        # 혜택 정보가 없는 카드 → 단일 청크
        if not benefits:
            chunk_text = (
                f"카드명: {card_name}\n"
                f"분류: {card_type}\n"
                f"연회비: 국내 {fee_dom}원, 해외 {fee_ovs}원\n"
                f"이 카드는 특별한 상세 혜택 요약 정보가 없습니다."
            )
            semantic_docs.append(Document(page_content=chunk_text, metadata=base_meta))
            continue

        # 혜택 1개 = Document 1개 (시맨틱 청킹)
        for b in benefits:
            clean_benefit = b[:MAX_BENEFIT_LEN]
            chunk_text = (
                f"카드명: {card_name}\n"
                f"분류: {card_type}\n"
                f"혜택 내용: {clean_benefit}"
            )
            semantic_docs.append(Document(page_content=chunk_text, metadata=base_meta))

    print(f"✂️  청킹 완료: {len(card_data)}개 카드 → {len(semantic_docs)}개 청크")
    return semantic_docs


def build_chroma_db(docs: list[Document], api_key: str) -> None:
    # 기존 DB 삭제
    if os.path.exists(PERSIST_DIR):
        print(f"🧹 기존 DB 폴더 '{PERSIST_DIR}' 삭제 중...")
        shutil.rmtree(PERSIST_DIR)

    print(f"🚀 OpenAI 임베딩 시작... (청크 수: {len(docs)}개)")
    print("   ※ API 호출 중이므로 잠시 기다려 주세요 (약 1~3분)")

    embeddings = OpenAIEmbeddings(api_key=api_key, model=EMBED_MODEL)

    Chroma.from_documents(
        documents=docs,
        embedding=embeddings,
        persist_directory=PERSIST_DIR,
    )

    print(f"🎉 DB 생성 완료! '{PERSIST_DIR}' 폴더에 저장되었습니다.")


def main():
    print("=" * 55)
    print("  CardMate · Chroma DB 빌더")
    print("=" * 55)

    api_key   = load_api_key()
    card_data = load_card_data(DATA_FILE)
    docs      = build_semantic_docs(card_data)
    build_chroma_db(docs, api_key)

    print("\n✅ 완료! 이제 'streamlit run app.py' 로 앱을 실행하세요.")
    print(f"   (card_semantic_db_v3/ 폴더는 .gitignore에 추가하는 것을 잊지 마세요!)\n")


if __name__ == "__main__":
    main()
