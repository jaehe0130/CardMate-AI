import json
from pathlib import Path
from typing import List, Dict, Any

from langchain_core.documents import Document

DATA_PATH = Path("data/card_data.json")


def load_card_data() -> List[Dict[str, Any]]:
    if not DATA_PATH.exists():
        raise FileNotFoundError(f"카드 데이터 파일이 없습니다: {DATA_PATH}")

    with open(DATA_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, list):
        raise ValueError("card_data.json은 리스트(list) 형태여야 합니다.")

    return data


def safe_str(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def card_to_document(card: Dict[str, Any]) -> Document:
    card_name = safe_str(card.get("Card_Name"))
    company = safe_str(card.get("Card_Company"))
    brands = safe_str(card.get("Brands"))
    event_benefit = safe_str(card.get("Event_Benefit"))
    benefits_structured = safe_str(card.get("Benefits_Structured"))
    annual_fee = safe_str(card.get("Annual_Fee"))
    base_performance = safe_str(card.get("Base_Performance"))
    card_type = safe_str(card.get("Card_Type"))
    source_url = safe_str(card.get("Source_URL"))
    image_url = safe_str(card.get("Image_URL"))

    page_content = f"""
카드명: {card_name}
카드사: {company}
카드종류: {card_type}
브랜드: {brands}
주요혜택: {event_benefit}
상세혜택: {benefits_structured}
연회비: {annual_fee}
전월실적: {base_performance}
""".strip()

    metadata = {
        "card_name": card_name,
        "company": company,
        "card_type": card_type,
        "brands": brands,
        "annual_fee": annual_fee,
        "performance": base_performance,
        "source_url": source_url,
        "image_url": image_url,
    }

    return Document(page_content=page_content, metadata=metadata)


def cards_to_documents(cards: List[Dict[str, Any]]) -> List[Document]:
    return [card_to_document(card) for card in cards]


def format_docs(docs: List[Document]) -> str:
    formatted_docs = []

    for doc in docs:
        content = doc.page_content
        fee = doc.metadata.get("annual_fee", "정보없음")
        perf = doc.metadata.get("performance", "정보없음")
        card_name = doc.metadata.get("card_name", "카드명 없음")

        full_text = (
            f"[카드명] {card_name}\n"
            f"{content}\n"
            f"[조건] 연회비: {fee} / 전월실적: {perf}"
        )
        formatted_docs.append(full_text)

    return "\n\n---\n\n".join(formatted_docs)
