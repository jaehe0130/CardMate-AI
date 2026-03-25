import json
from pathlib import Path
from typing import Any, Dict, List
from functools import lru_cache

from langchain_core.documents import Document

CARD_DATA_PATH = Path("data/card_data.json")
TOP_CARD_DATA_PATH = Path("data/top_card_data.json")


def safe_str(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


@lru_cache(maxsize=1)
def load_card_data() -> List[Dict[str, Any]]:
    if not CARD_DATA_PATH.exists():
        raise FileNotFoundError(f"카드 데이터 파일이 없습니다: {CARD_DATA_PATH}")

    with open(CARD_DATA_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, list):
        raise ValueError("data/card_data.json은 리스트(list) 형태여야 합니다.")

    return data


@lru_cache(maxsize=1)
def load_top_card_dict() -> Dict[tuple, Dict[str, Any]]:
    if not TOP_CARD_DATA_PATH.exists():
        return {}

    try:
        with open(TOP_CARD_DATA_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)

        if not isinstance(data, list):
            return {}

        result = {}
        for item in data:
            if not isinstance(item, dict):
                continue

            company = safe_str(item.get("Card_Company")).lower()
            name = safe_str(item.get("Card_Name")).lower()
            card_type = safe_str(item.get("Card_Type")).lower()

            if not company or not name or not card_type:
                continue

            result[(company, name, card_type)] = item

        return result

    except Exception:
        return {}


def card_to_semantic_documents(card: Dict[str, Any]) -> List[Document]:
    card_name = safe_str(card.get("Card_Name", "이름 없음"))
    card_type = safe_str(card.get("Card_Type", "구분 없음"))
    company = safe_str(card.get("Card_Company", "카드사 없음"))

    perf_num = card.get("Base_Perf_Num", 0)
    perf_text = safe_str(card.get("Base_Performance", "정보없음"))

    fee_dom = safe_str(card.get("Annual_Fee_Domestic", 0))
    fee_ovs = safe_str(card.get("Annual_Fee_Overseas", 0))
    annual_fee = safe_str(card.get("Annual_Fee", ""))

    image_url = safe_str(card.get("Image_URL", ""))
    source_url = safe_str(card.get("Source_URL", ""))

    benefits = card.get("Benefits_Summary", [])
    docs: List[Document] = []

    metadata = {
        "card_name": card_name,
        "card_company": company,
        "card_type": card_type,
        "performance": perf_text if perf_text else perf_num,
        "annual_fee": annual_fee if annual_fee else f"국내 {fee_dom} / 해외 {fee_ovs}",
        "annual_fee_domestic": fee_dom,
        "annual_fee_overseas": fee_ovs,
        "image_url": image_url,
        "source_url": source_url,
    }

    if not benefits:
        chunk_text = (
            f"카드명: {card_name}\n"
            f"분류: {card_type}\n"
            f"카드사: {company}\n"
            f"연회비: 국내 {fee_dom}원, 해외 {fee_ovs}원\n"
            f"전월실적: {perf_text}\n"
            f"이 카드는 특별한 상세 혜택 요약 정보가 없습니다."
        )
        docs.append(Document(page_content=chunk_text, metadata=metadata))
        return docs

    for benefit in benefits:
        chunk_text = (
            f"카드명: {card_name}\n"
            f"분류: {card_type}\n"
            f"카드사: {company}\n"
            f"혜택 내용: {benefit}"
        )
        docs.append(Document(page_content=chunk_text, metadata=metadata))

    return docs


def cards_to_semantic_documents(cards: List[Dict[str, Any]]) -> List[Document]:
    docs: List[Document] = []
    for card in cards:
        docs.extend(card_to_semantic_documents(card))
    return docs


def format_docs(docs: List[Document]) -> str:
    formatted = []
    for idx, d in enumerate(docs):
        fee = d.metadata.get("annual_fee", "정보없음")
        perf = d.metadata.get("performance", "정보없음")
        card_name = d.metadata.get("card_name", "카드명 없음")

        formatted.append(
            f"[[추천 {idx+1}]]\n"
            f"### {card_name} ###\n"
            f"{d.page_content}\n"
            f"[조건] 연회비: {fee} / 전월실적: {perf}"
        )

    return "\n\n".join(formatted)
