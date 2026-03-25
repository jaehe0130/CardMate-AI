from typing import List, Dict, Any
from utils import build_card_text, get_base_perf_num


# 사용처별 키워드 사전
KEYWORD_MAP = {
    "카페": ["카페", "커피", "스타벅스", "투썸", "이디야", "음료"],
    "편의점": ["편의점", "cu", "gs25", "세븐일레븐"],
    "교통": ["교통", "버스", "지하철", "대중교통", "택시", "후불교통"],
    "쇼핑": ["쇼핑", "온라인", "쿠팡", "11번가", "g마켓", "옥션", "네이버페이", "무신사"],
    "해외결제": ["해외", "해외결제", "해외이용", "visa", "master", "mastercard", "amex"],
    "배달": ["배달", "배달의민족", "배민", "요기요", "쿠팡이츠"],
    "통신": ["통신", "skt", "kt", "lg", "lg u+", "u+"],
    "주유": ["주유", "주유소", "sk에너지", "gs칼텍스", "s-oil", "현대오일뱅크"],
    "마트": ["마트", "이마트", "홈플러스", "롯데마트", "코스트코"],
    "간편결제": ["간편결제", "삼성페이", "애플페이", "카카오페이", "네이버페이", "pay"],
}


def _score_card_type(card_text: str, card_type: str) -> int:
    """카드 종류(신용/체크)에 대한 점수"""
    if not card_type:
        return 0

    if card_type == "상관없음":
        return 4

    if card_type == "신용카드":
        if "신용" in card_text or "credit" in card_text:
            return 18
        return 0

    if card_type == "체크카드":
        if "체크" in card_text or "check" in card_text:
            return 18
        return 0

    return 0


def _score_usage(card_text: str, usage: str, weight: int) -> int:
    """주 사용처/추가 사용처 점수"""
    if not usage or usage not in KEYWORD_MAP:
        return 0

    score = 0
    matched_keywords = 0

    for kw in KEYWORD_MAP[usage]:
        if kw.lower() in card_text:
            matched_keywords += 1

    if matched_keywords == 0:
        return 0

    # 키워드가 많이 맞을수록 조금 더 가산
    score += weight
    score += min(matched_keywords, 3) * 2

    return score


def _score_monthly_spend(perf_num: int, monthly_spend: str) -> int:
    """전월 실적과 사용자의 월 사용액 적합도"""
    if not monthly_spend:
        return 0

    if perf_num is None:
        perf_num = 9999

    if monthly_spend == "30만원 이하":
        if perf_num <= 30:
            return 14
        elif perf_num <= 50:
            return 7
        elif perf_num <= 70:
            return 2
        return -4

    if monthly_spend == "30~70만원":
        if perf_num <= 30:
            return 8
        elif perf_num <= 70:
            return 14
        elif perf_num <= 100:
            return 6
        return -3

    if monthly_spend == "70만원 이상":
        if perf_num <= 30:
            return 6
        elif perf_num <= 70:
            return 10
        elif perf_num <= 100:
            return 12
        return 4

    return 0


def _score_bonus(card_text: str, answers: Dict[str, Any]) -> int:
    """
    자잘한 보너스 점수
    - 주 사용처와 추가 사용처가 모두 반영된 카드에 가산
    - broad benefit 카드에 아주 약한 보너스
    """
    score = 0

    main_use = answers.get("main_use")
    extra_use = answers.get("extra_use")

    # 주 사용처와 추가 사용처 둘 다 일부라도 매칭되면 보너스
    main_hit = False
    extra_hit = False

    if main_use in KEYWORD_MAP:
        main_hit = any(kw.lower() in card_text for kw in KEYWORD_MAP[main_use])

    if extra_use in KEYWORD_MAP:
        extra_hit = any(kw.lower() in card_text for kw in KEYWORD_MAP[extra_use])

    if main_hit and extra_hit:
        score += 6

    # 범용 혜택 카드에 약간의 가산
    broad_keywords = ["할인", "적립", "캐시백", "포인트"]
    broad_hits = sum(1 for kw in broad_keywords if kw in card_text)
    score += min(broad_hits, 2)

    return score


def score_card(card: Dict[str, Any], answers: Dict[str, Any]) -> int:
    """
    카드 1개에 대한 최종 점수 계산
    """
    card_text = build_card_text(card)
    perf_num = get_base_perf_num(card)

    card_type = answers.get("card_type", "")
    main_use = answers.get("main_use", "")
    monthly_spend = answers.get("monthly_spend", "")
    extra_use = answers.get("extra_use", "")

    score = 0

    # 1) 카드 타입
    score += _score_card_type(card_text, card_type)

    # 2) 주 사용처
    score += _score_usage(card_text, main_use, weight=14)

    # 3) 추가 사용처
    score += _score_usage(card_text, extra_use, weight=8)

    # 4) 전월 실적 적합도
    score += _score_monthly_spend(perf_num, monthly_spend)

    # 5) 보너스
    score += _score_bonus(card_text, answers)

    return score


def recommend_cards(
    card_list: List[Dict[str, Any]],
    answers: Dict[str, Any],
    top_k: int = 3
) -> List[Dict[str, Any]]:
    """
    점수가 높은 순으로 카드 추천
    """
    scored_cards = []

    for card in card_list:
        score = score_card(card, answers)
        scored_cards.append((score, card))

    scored_cards.sort(key=lambda x: x[0], reverse=True)

    return [card for score, card in scored_cards[:top_k]]


def recommend_cards_with_scores(
    card_list: List[Dict[str, Any]],
    answers: Dict[str, Any],
    top_k: int = 3
) -> List[Dict[str, Any]]:
    """
    점수까지 포함해서 보고 싶을 때 사용하는 디버깅/개발용 함수
    """
    scored_cards = []

    for card in card_list:
        score = score_card(card, answers)
        enriched = dict(card)
        enriched["_score"] = score
        scored_cards.append(enriched)

    scored_cards.sort(key=lambda x: x["_score"], reverse=True)

    return scored_cards[:top_k]
