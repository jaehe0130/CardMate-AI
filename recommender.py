import json


def load_card_data():
    with open("data/card_data.json", "r", encoding="utf-8") as f:
        return json.load(f)


def filter_cards(cards, preferences):
    filtered = []

    for card in cards:
        card_type = str(card.get("Card_Type", ""))
        annual_fee = str(card.get("Annual_Fee_Domestic", card.get("Annual_Fee", "")))
        perf = str(card.get("Base_Performance", ""))
        benefits = str(card.get("Benefits_Structured", ""))
        brands = str(card.get("Brands", ""))

        # 카드 종류
        if preferences["card_type"]:
            if preferences["card_type"] not in card_type:
                continue

        # 혜택 키워드
        if preferences["benefit_categories"]:
            text = f"{benefits} {brands}"
            if not any(cat in text for cat in preferences["benefit_categories"]):
                continue

        filtered.append(card)

    return filtered


def make_card_payload(card):
    return {
        "card_name": card.get("Card_Name", ""),
        "company": card.get("Card_Company", ""),
        "annual_fee": card.get("Annual_Fee_Domestic", card.get("Annual_Fee", "")),
        "base_perf": card.get("Base_Performance", ""),
        "benefits": str(card.get("Benefits_Structured", ""))[:180],
        "image_url": card.get("Image_URL", ""),
        "source_url": card.get("Source_URL", "")
    }


def make_mock_result(cards, preferences):
    selected = cards[:2]

    if not selected:
        return {
            "result": "조건에 맞는 카드가 없어요. 카드 종류나 혜택 조건을 조금 완화해보세요.",
            "cards": []
        }

    card_names = [c.get("Card_Name", "") for c in selected]
    categories = preferences.get("benefit_categories", [])

    result_text = f"""
1. 소비 성향 분석
- 사용자는 {", ".join(categories)} 중심의 생활비 절약형 소비 패턴을 가지고 있습니다.

2. 추천 카드 1
- 카드명: {card_names[0] if len(card_names) > 0 else "-"}
- 추천 이유: 사용자의 주요 소비 카테고리와 맞는 혜택을 기대할 수 있습니다.
- 핵심 혜택: 생활밀착형 할인 중심
- 실적/연회비: 카드 상세 조건 확인 필요
- 주의점: 월 할인한도와 전월실적 조건을 함께 확인하세요.

3. 추천 카드 2
- 카드명: {card_names[1] if len(card_names) > 1 else "-"}
- 추천 이유: 첫 번째 카드와 함께 비교했을 때 대체 옵션이 될 수 있습니다.
- 핵심 혜택: 소비처 분산형 혜택
- 실적/연회비: 카드 상세 조건 확인 필요
- 주의점: 실제 혜택 적용 업종을 확인하세요.

4. 비교
- 첫 번째 카드는 주력 생활비 카테고리에, 두 번째 카드는 대안 카드로 검토하기 좋습니다.
""".strip()

    return {
        "result": result_text,
        "cards": [make_card_payload(c) for c in selected]
    }


def get_card_recommendation(user_input: str, preferences: dict, api_key: str | None = None):
    """
    현재는 mock 추천.
    나중에 실제 RAG/LLM 모델로 바꿀 위치.
    """
    cards = load_card_data()
    filtered_cards = filter_cards(cards, preferences)
    return make_mock_result(filtered_cards, preferences)
