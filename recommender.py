from typing import List, Dict, Any
from utils import build_card_text, get_base_perf_num

KEYWORD_MAP = {
    "카페": ["카페", "커피", "스타벅스", "투썸", "이디야", "음료"],
    "편의점": ["편의점", "cu", "gs25", "세븐일레븐"],
    "교통": ["교통", "버스", "지하철", "대중교통", "택시", "후불교통"],
    "쇼핑": ["쇼핑", "온라인", "쿠팡", "11번가", "g마켓", "옥션", "네이버페이", "무신사"],
    "해외결제": ["해외", "해외결제", "해외이용", "visa", "master", "mastercard", "amex"],
    "배달": ["배달", "배달의민족", "배민", "요기요", "쿠팡이츠"],
    "통신": ["통신", "skt", "kt", "lg", "lg u+", "u+"],
}

def _score_card_type(card_text: str, card_type: str) -> int:
    if not card_type:
        return 0
    if card_type == "상관없음":
        return 4
    if card_type == "신용카드":
        return 18 if ("신용" in card_text or "credit" in card_text) else 0
    if card_type == "체크카드":
        return 18 if ("체크" in card_text or "check" in card_text) else 0
    return 0

def _score_usage(card_text: str, usage: str, weight: int) -> int:
    if not usage or usage not in KEYWORD_MAP:
        return 0

    matched = 0
    for kw in KEYWORD_MAP[usage]:
        if kw.lower() in card_text:
            matched += 1

    if matched == 0:
        return 0

    return weight + min(matched, 3) * 2

def _score_monthly_spend(perf_num: int, monthly_spend: str) -> int:
    if not monthly_spend:
        return 0

    if monthly_spend == "30만원 이하":
        if perf_num <= 30:
            return 14
        if perf_num <= 50:
            return 7
        if perf_num <= 70:
            return 2
        return -4

    if monthly_spend == "30~70만원":
        if perf_num <= 30:
            return 8
        if perf_num <= 70:
            return 14
        if perf_num <= 100:
            return 6
        return -3

    if monthly_spend == "70만원 이상":
        if perf_num <= 30:
            return 6
        if perf_num <= 70:
            return 10
        if perf_num <= 100:
            return 12
        return 4

    return 0

def _score_bonus(card_text: str, answers: Dict[str, Any]) -> int:
    score = 0
    main_use = answers.get("main_use")
    extra_use = answers.get("extra_use")

    main_hit = False
    extra_hit = False

    if main_use in KEYWORD_MAP:
        main_hit = any(kw.lower() in card_text for kw in KEYWORD_MAP[main_use])

    if extra_use in KEYWORD_MAP:
        extra_hit = any(kw.lower() in card_text for kw in KEYWORD_MAP[extra_use])

    if main_hit and extra_hit:
        score += 6

    broad_keywords = ["할인", "적립", "캐시백", "포인트"]
    score += min(sum(1 for kw in broad_keywords if kw in card_text), 2)

    return score

def score_card(card: Dict[str, Any], answers: Dict[str, Any]) -> int:
    card_text = build_card_text(card)
    perf_num = get_base_perf_num(card)

    score = 0
    score += _score_card_type(card_text, answers.get("card_type", ""))
    score += _score_usage(card_text, answers.get("main_use", ""), weight=14)
    score += _score_usage(card_text, answers.get("extra_use", ""), weight=8)
    score += _score_monthly_spend(perf_num, answers.get("monthly_spend", ""))
    score += _score_bonus(card_text, answers)
    return score

def recommend_cards(card_list: List[Dict[str, Any]], answers: Dict[str, Any], top_k: int = 3) -> List[Dict[str, Any]]:
    scored_cards = []
    for card in card_list:
        score = score_card(card, answers)
        scored_cards.append((score, card))

    scored_cards.sort(key=lambda x: x[0], reverse=True)
    return [card for score, card in scored_cards[:top_k]]
