import json
from pathlib import Path
from typing import List, Dict, Any


DATA_PATH = Path("data/card_data.json")


def load_card_data() -> List[Dict[str, Any]]:
    """카드 JSON 데이터 로드"""
    if not DATA_PATH.exists():
        raise FileNotFoundError(f"카드 데이터 파일이 없습니다: {DATA_PATH}")

    with open(DATA_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, list):
        raise ValueError("card_data.json 형식이 올바르지 않습니다. 리스트 형태여야 합니다.")

    return data


def safe_str(value: Any) -> str:
    """None이나 비문자값을 안전하게 문자열로 변환"""
    if value is None:
        return ""
    return str(value).strip()


def build_card_text(card: Dict[str, Any]) -> str:
    """카드 검색/추천용 통합 텍스트"""
    fields = [
        card.get("Card_Company", ""),
        card.get("Card_Name", ""),
        card.get("Brands", ""),
        card.get("Event_Benefit", ""),
        card.get("Benefits_Structured", ""),
        card.get("Annual_Fee", ""),
        card.get("Base_Performance", ""),
        card.get("Card_Type", ""),
    ]
    return " ".join([safe_str(x) for x in fields]).lower()


def get_card_image(card: Dict[str, Any]) -> str:
    return safe_str(card.get("Image_URL", ""))


def get_card_name(card: Dict[str, Any]) -> str:
    return safe_str(card.get("Card_Name", "이름 없는 카드"))


def get_card_company(card: Dict[str, Any]) -> str:
    return safe_str(card.get("Card_Company", ""))


def get_card_type(card: Dict[str, Any]) -> str:
    return safe_str(card.get("Card_Type", ""))


def get_card_benefit(card: Dict[str, Any]) -> str:
    benefit = safe_str(card.get("Event_Benefit", ""))
    structured = safe_str(card.get("Benefits_Structured", ""))
    return benefit if benefit else structured


def get_card_annual_fee(card: Dict[str, Any]) -> str:
    return safe_str(card.get("Annual_Fee", "정보 없음"))


def get_card_perf(card: Dict[str, Any]) -> str:
    return safe_str(card.get("Base_Performance", "정보 없음"))


def get_card_brands(card: Dict[str, Any]) -> List[str]:
    raw = safe_str(card.get("Brands", ""))
    if not raw:
        return []
    return [x.strip() for x in raw.split(",") if x.strip()]


def get_card_url(card: Dict[str, Any]) -> str:
    return safe_str(card.get("Source_URL", ""))


def get_base_perf_num(card: Dict[str, Any]) -> int:
    """전월 실적 숫자 추출용"""
    raw = card.get("Base_Perf_Num", 9999)
    try:
        return int(raw)
    except Exception:
        return 9999


def summarize_user_profile(answers: Dict[str, Any]) -> str:
    """사용자 답변 요약"""
    card_type = answers.get("card_type", "상관없음")
    main_use = answers.get("main_use", "미선택")
    monthly_spend = answers.get("monthly_spend", "미선택")
    extra_use = answers.get("extra_use", "미선택")

    return (
        f"원하시는 카드는 **{card_type}**이고, "
        f"주 사용 목적은 **{main_use}**, "
        f"월 사용액은 **{monthly_spend}**, "
        f"추가 선호 업종은 **{extra_use}**로 이해했어요."
    )
