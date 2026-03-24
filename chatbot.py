from recommender import get_card_recommendation


def init_session_state():
    import streamlit as st

    if "messages" not in st.session_state:
        st.session_state.messages = [
            {
                "role": "assistant",
                "content": "안녕하세요. 자주 쓰는 소비처와 원하는 조건을 말해주시면 카드 추천을 도와드릴게요."
            }
        ]

    if "user_prefs" not in st.session_state:
        st.session_state.user_prefs = {
            "card_type": None,
            "benefit_categories": [],
            "max_annual_fee_domestic": None,
            "max_base_perf_num": None
        }

    if "last_cards" not in st.session_state:
        st.session_state.last_cards = []


def extract_user_preferences(user_text: str):
    prefs = {
        "card_type": None,
        "benefit_categories": [],
        "max_annual_fee_domestic": None,
        "max_base_perf_num": None
    }

    text = user_text.lower()

    if "신용" in user_text:
        prefs["card_type"] = "신용카드"
    elif "체크" in user_text:
        prefs["card_type"] = "체크카드"

    keyword_map = {
        "편의점": ["편의점", "cu", "gs25", "세븐일레븐"],
        "공과금": ["공과금", "관리비", "전기요금", "도시가스", "수도요금"],
        "통신비": ["통신", "통신비", "skt", "kt", "lg"],
        "카페": ["카페", "스타벅스", "커피"],
        "교통": ["교통", "버스", "지하철", "택시"],
        "마트": ["마트", "이마트", "홈플러스", "롯데마트"],
        "주유": ["주유", "주유소"],
        "배달": ["배달", "배달의민족", "요기요", "쿠팡이츠"],
    }

    for cat, keywords in keyword_map.items():
        if any(k in text for k in keywords):
            prefs["benefit_categories"].append(cat)

    if "실적" in user_text and ("낮" in user_text or "부담" in user_text or "너무 높" in user_text):
        prefs["max_base_perf_num"] = 300000

    if "연회비" in user_text and ("낮" in user_text or "저렴" in user_text or "부담" in user_text):
        prefs["max_annual_fee_domestic"] = 20000

    return prefs


def update_preferences(old_prefs: dict, new_prefs: dict):
    if new_prefs["card_type"]:
        old_prefs["card_type"] = new_prefs["card_type"]

    if new_prefs["benefit_categories"]:
        merged = set(old_prefs.get("benefit_categories", [])) | set(new_prefs["benefit_categories"])
        old_prefs["benefit_categories"] = list(merged)

    if new_prefs["max_annual_fee_domestic"] is not None:
        old_prefs["max_annual_fee_domestic"] = new_prefs["max_annual_fee_domestic"]

    if new_prefs["max_base_perf_num"] is not None:
        old_prefs["max_base_perf_num"] = new_prefs["max_base_perf_num"]

    return old_prefs


def merge_sidebar_preferences(current_prefs: dict, sidebar_filters: dict):
    if sidebar_filters["card_type"] is not None:
        current_prefs["card_type"] = sidebar_filters["card_type"]

    if sidebar_filters["max_base_perf_num"] is not None:
        current_prefs["max_base_perf_num"] = sidebar_filters["max_base_perf_num"]

    if sidebar_filters["max_annual_fee_domestic"] is not None:
        current_prefs["max_annual_fee_domestic"] = sidebar_filters["max_annual_fee_domestic"]

    if sidebar_filters["benefit_categories"]:
        current_prefs["benefit_categories"] = sidebar_filters["benefit_categories"]

    return current_prefs


def is_ready_for_recommendation(prefs: dict):
    if not prefs.get("card_type"):
        return False, "신용카드와 체크카드 중 어떤 카드를 찾으시는지 알려주세요."

    if not prefs.get("benefit_categories"):
        return False, "편의점, 통신비, 공과금, 카페, 교통 중 자주 쓰는 소비처를 알려주세요."

    return True, None


def process_user_input(user_input: str, sidebar_filters: dict, api_key: str | None):
    import streamlit as st

    current_prefs = st.session_state.user_prefs.copy()

    new_prefs = extract_user_preferences(user_input)
    current_prefs = update_preferences(current_prefs, new_prefs)
    current_prefs = merge_sidebar_preferences(current_prefs, sidebar_filters)

    ready, followup = is_ready_for_recommendation(current_prefs)

    if not ready:
        return {
            "message": followup,
            "preferences": current_prefs,
            "cards": []
        }

    response = get_card_recommendation(
        user_input=user_input,
        preferences=current_prefs,
        api_key=api_key
    )

    return {
        "message": response["result"],
        "preferences": current_prefs,
        "cards": response["cards"]
    }
