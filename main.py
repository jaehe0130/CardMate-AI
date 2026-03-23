import json
import re
from pathlib import Path
from typing import Any, Dict, List

import streamlit as st
from openai import OpenAI

# =========================================================
# 기본 설정
# =========================================================
st.set_page_config(
    page_title="AI 카드 추천 챗봇",
    page_icon="💳",
    layout="wide"
)

client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

CREDIT_JSON = Path("credit_card.json")
CHECK_JSON = Path("check_card.json")

# =========================================================
# 스타일
# =========================================================
st.markdown("""
<style>
.block-container {
    padding-top: 1.3rem;
    padding-bottom: 2rem;
    max-width: 1240px;
}
.title {
    font-size: 2rem;
    font-weight: 800;
    margin-bottom: 0.2rem;
}
.subtitle {
    color: #666;
    margin-bottom: 1rem;
}
.info-box {
    padding: 0.9rem 1rem;
    border-radius: 16px;
    background: #f7f8fa;
    border: 1px solid #edf0f3;
    margin-bottom: 0.8rem;
}
.card-box {
    padding: 1rem;
    border-radius: 18px;
    background: #fff;
    border: 1px solid #ececec;
    box-shadow: 0 6px 18px rgba(0,0,0,0.05);
    margin-bottom: 1rem;
}
.badge {
    display: inline-block;
    padding: 0.22rem 0.58rem;
    margin-right: 0.3rem;
    margin-bottom: 0.35rem;
    border-radius: 999px;
    background: #f1f3f5;
    font-size: 0.82rem;
}
.small {
    color: #666;
    font-size: 0.92rem;
}
</style>
""", unsafe_allow_html=True)

# =========================================================
# 선택지
# =========================================================
CARD_TYPE_OPTIONS = ["신용카드", "체크카드", "상관없음"]
SPEND_OPTIONS = ["20만원 이하", "20~40만원", "40~60만원", "60~80만원", "80~120만원", "120만원 이상"]
FEE_OPTIONS = ["연회비 없음", "1만원 이하", "2만원 이하", "3만원 이하", "5만원 이하"]
GOAL_OPTIONS = ["생활비 절약", "할인 많이 받기", "포인트/적립 위주", "교통/카페 특화", "배달/편의점 특화", "쇼핑 특화", "여행/마일리지"]
LIFESTYLE_OPTIONS = ["사회초년생", "직장인", "대학생", "자취생", "프리랜서", "기타"]
CATEGORY_OPTIONS = ["카페", "대중교통", "배달", "편의점", "통신비", "쇼핑", "주유", "OTT/구독", "여행", "공과금", "마트", "없음"]
PERFORMANCE_OPTIONS = ["상관없음", "전월실적 없는 카드 선호", "전월실적 있어도 괜찮음"]
SIMPLE_OPTIONS = ["상관없음", "혜택 조건 단순한 카드 선호", "조건 복잡해도 혜택 크면 괜찮음"]
ISSUER_OPTIONS = ["없음", "신한카드", "KB국민카드", "현대카드", "삼성카드", "우리카드", "하나카드", "롯데카드", "BC카드", "카카오뱅크", "토스", "기타"]

# =========================================================
# 세션
# =========================================================
def init_session():
    if "messages" not in st.session_state:
        st.session_state.messages = [
            {
                "role": "assistant",
                "content": "안녕하세요. 카드 데이터를 먼저 좁힌 뒤, 그 후보 안에서 가장 잘 맞는 카드 3개를 추천해드릴게요."
            }
        ]

    if "user_profile" not in st.session_state:
        st.session_state.user_profile = {
            "card_type": "상관없음",
            "monthly_spend": "40~60만원",
            "annual_fee_limit": "2만원 이하",
            "main_goal": "생활비 절약",
            "lifestyle": "사회초년생",
            "top_category_1": "카페",
            "top_category_2": "대중교통",
            "top_category_3": "배달",
            "performance_preference": "상관없음",
            "benefit_style": "상관없음",
            "preferred_issuer": "없음",
            "excluded_issuer": "없음",
        }

    if "all_cards" not in st.session_state:
        st.session_state.all_cards = []

    if "candidate_cards" not in st.session_state:
        st.session_state.candidate_cards = []

    if "recommendations" not in st.session_state:
        st.session_state.recommendations = []

    if "started" not in st.session_state:
        st.session_state.started = False

init_session()

# =========================================================
# 유틸
# =========================================================
def add_message(role: str, content: str):
    st.session_state.messages.append({"role": role, "content": content})

def safe_int(value: Any, default: int = 0) -> int:
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if value is None:
        return default
    text = str(value).replace(",", "")
    nums = re.findall(r"\d+", text)
    if not nums:
        return default
    return int("".join(nums))

def first_non_empty(data: Dict[str, Any], keys: List[str], default=None):
    for k in keys:
        if k in data and data[k] not in [None, "", [], {}]:
            return data[k]
    return default

def spend_to_number(text: str) -> int:
    mapping = {
        "20만원 이하": 200000,
        "20~40만원": 400000,
        "40~60만원": 600000,
        "60~80만원": 800000,
        "80~120만원": 1200000,
        "120만원 이상": 1600000
    }
    return mapping.get(text, 600000)

def fee_to_number(text: str) -> int:
    mapping = {
        "연회비 없음": 0,
        "1만원 이하": 10000,
        "2만원 이하": 20000,
        "3만원 이하": 30000,
        "5만원 이하": 50000
    }
    return mapping.get(text, 20000)

def get_top_categories(profile: Dict[str, Any]) -> List[str]:
    values = [
        profile.get("top_category_1"),
        profile.get("top_category_2"),
        profile.get("top_category_3"),
    ]
    result = []
    for v in values:
        if v and v != "없음" and v not in result:
            result.append(v)
    return result

def normalize_benefits(raw: Dict[str, Any]) -> List[str]:
    benefit_list = first_non_empty(raw, ["benefits", "benefit_categories", "main_benefits"], [])
    if isinstance(benefit_list, list):
        return [str(x).strip() for x in benefit_list if str(x).strip()]

    text_pool = " ".join([
        str(first_non_empty(raw, ["benefit_text"], "")),
        str(first_non_empty(raw, ["description"], "")),
        str(first_non_empty(raw, ["summary"], "")),
        str(first_non_empty(raw, ["benefit"], "")),
    ])

    category_map = {
        "카페": ["카페", "스타벅스", "커피"],
        "대중교통": ["교통", "버스", "지하철", "대중교통"],
        "배달": ["배달", "배달앱", "배민", "요기요", "쿠팡이츠"],
        "편의점": ["편의점", "CU", "GS25", "세븐일레븐"],
        "통신비": ["통신", "통신비"],
        "쇼핑": ["쇼핑", "온라인쇼핑", "쿠팡", "네이버쇼핑", "G마켓"],
        "주유": ["주유", "주유소", "기름"],
        "OTT/구독": ["OTT", "넷플릭스", "유튜브프리미엄", "디즈니", "구독"],
        "여행": ["여행", "항공", "마일리지", "호텔"],
        "공과금": ["공과금", "전기", "가스", "수도"],
        "마트": ["마트", "이마트", "홈플러스", "롯데마트"]
    }

    found = []
    for cat, keywords in category_map.items():
        if any(k in text_pool for k in keywords):
            found.append(cat)
    return found

def normalize_card(raw: Dict[str, Any], source_type: str) -> Dict[str, Any]:
    card_name = first_non_empty(raw, ["card_name", "name", "cardName", "상품명"], "이름없음 카드")
    issuer = first_non_empty(raw, ["issuer", "card_company", "company", "brand", "card_corp"], "카드사 미상")
    annual_fee = safe_int(first_non_empty(raw, ["annual_fee", "fee", "annualFee", "연회비"], 0), 0)
    min_spend = safe_int(first_non_empty(raw, ["min_spend", "previous_month_spend", "pre_spend", "전월실적"], 0), 0)
    image_url = first_non_empty(raw, ["Image_URL", "image_url", "img_url", "card_image", "image"], None)
    benefit_detail = first_non_empty(raw, ["benefit_detail", "benefits_detail", "benefit_map"], {})
    description_parts = []
    for k in ["summary", "description", "benefit_text", "benefit", "intro"]:
        if raw.get(k):
            description_parts.append(str(raw.get(k)))
    description = " ".join(description_parts).strip()

    if not isinstance(benefit_detail, dict):
        benefit_detail = {}

    return {
        "card_name": str(card_name),
        "issuer": str(issuer),
        "annual_fee": annual_fee,
        "min_spend": min_spend,
        "benefits": normalize_benefits(raw),
        "benefit_detail": benefit_detail,
        "description": description,
        "image_url": image_url,
        "card_type": "체크카드" if source_type == "check" else "신용카드",
        "raw": raw,
    }

def load_json_cards(path: Path, source_type: str) -> List[Dict[str, Any]]:
    if not path.exists():
        return []

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    if isinstance(data, dict):
        for v in data.values():
            if isinstance(v, list):
                data = v
                break

    if not isinstance(data, list):
        return []

    return [normalize_card(item, source_type) for item in data if isinstance(item, dict)]

def load_all_cards() -> List[Dict[str, Any]]:
    return load_json_cards(CREDIT_JSON, "credit") + load_json_cards(CHECK_JSON, "check")

def card_to_search_text(card: Dict[str, Any]) -> str:
    detail_text = ""
    if card.get("benefit_detail"):
        try:
            detail_text = json.dumps(card["benefit_detail"], ensure_ascii=False)
        except Exception:
            detail_text = str(card["benefit_detail"])

    return " ".join([
        str(card.get("card_name", "")),
        str(card.get("issuer", "")),
        str(card.get("card_type", "")),
        " ".join(card.get("benefits", [])),
        str(card.get("description", "")),
        detail_text,
    ]).lower()

# =========================================================
# 후보 축소
# =========================================================
def hard_filter_cards(cards: List[Dict[str, Any]], profile: Dict[str, Any]) -> List[Dict[str, Any]]:
    fee_limit = fee_to_number(profile["annual_fee_limit"])
    spend_limit = spend_to_number(profile["monthly_spend"])

    results = []
    for card in cards:
        # 카드 종류
        if profile["card_type"] != "상관없음" and card["card_type"] != profile["card_type"]:
            continue

        # 연회비
        if fee_limit == 0:
            if card["annual_fee"] != 0:
                continue
        else:
            if card["annual_fee"] > fee_limit:
                continue

        # 전월실적 선호
        if profile["performance_preference"] == "전월실적 없는 카드 선호":
            if card["min_spend"] > 0:
                continue
        elif profile["performance_preference"] == "전월실적 있어도 괜찮음":
            # 너무 높은 전월실적은 제외
            if card["min_spend"] > spend_limit * 1.2:
                continue

        # 제외 카드사
        excluded = profile["excluded_issuer"]
        if excluded != "없음" and excluded in card["issuer"]:
            continue

        results.append(card)

    return results

def soft_rank_cards(cards: List[Dict[str, Any]], profile: Dict[str, Any], top_k: int = 25) -> List[Dict[str, Any]]:
    top_categories = get_top_categories(profile)

    query_tokens = []
    query_tokens.extend(top_categories)
    query_tokens.append(profile["main_goal"])
    query_tokens.append(profile["lifestyle"])

    if profile["preferred_issuer"] != "없음":
        query_tokens.append(profile["preferred_issuer"])

    if profile["benefit_style"] == "혜택 조건 단순한 카드 선호":
        query_tokens.extend(["기본", "단순", "무실적", "캐시백"])
    elif profile["benefit_style"] == "조건 복잡해도 혜택 크면 괜찮음":
        query_tokens.extend(["적립", "할인", "프리미엄"])

    query_tokens = [t.lower() for t in query_tokens if t and t != "없음"]

    scored = []
    for card in cards:
        text = card_to_search_text(card)
        score = 0

        # 선호 카드사
        if profile["preferred_issuer"] != "없음" and profile["preferred_issuer"] in card["issuer"]:
            score += 4

        # 주요 카테고리
        for cat in top_categories:
            if cat.lower() in text:
                score += 3

        # 목표
        goal = profile["main_goal"]
        if goal == "생활비 절약":
            for kw in ["할인", "캐시백", "생활", "편의점", "공과금"]:
                if kw in text:
                    score += 1
        elif goal == "할인 많이 받기":
            for kw in ["할인", "청구할인", "캐시백"]:
                if kw in text:
                    score += 1
        elif goal == "포인트/적립 위주":
            for kw in ["적립", "포인트", "마일리지"]:
                if kw in text:
                    score += 1
        elif goal == "교통/카페 특화":
            for kw in ["카페", "교통", "대중교통"]:
                if kw in text:
                    score += 2
        elif goal == "배달/편의점 특화":
            for kw in ["배달", "편의점"]:
                if kw in text:
                    score += 2
        elif goal == "쇼핑 특화":
            for kw in ["쇼핑", "온라인"]:
                if kw in text:
                    score += 2
        elif goal == "여행/마일리지":
            for kw in ["여행", "항공", "마일리지", "호텔"]:
                if kw in text:
                    score += 2

        # 생활패턴
        if profile["lifestyle"] in text:
            score += 1

        # 간단 토큰 매칭
        for token in query_tokens:
            if token in text:
                score += 1

        # 전월실적 낮을수록 약간 우대
        if card["min_spend"] == 0:
            score += 1

        scored.append((card, score))

    scored.sort(key=lambda x: x[1], reverse=True)
    return [x[0] for x in scored[:top_k]]

# =========================================================
# OpenAI 최종 추천
# =========================================================
def build_profile_summary(profile: Dict[str, Any]) -> str:
    return (
        f"카드종류={profile['card_type']}, "
        f"월소비={profile['monthly_spend']}, "
        f"연회비한도={profile['annual_fee_limit']}, "
        f"추천목표={profile['main_goal']}, "
        f"라이프스타일={profile['lifestyle']}, "
        f"주요카테고리={', '.join(get_top_categories(profile))}, "
        f"전월실적선호={profile['performance_preference']}, "
        f"혜택조건선호={profile['benefit_style']}, "
        f"선호카드사={profile['preferred_issuer']}, "
        f"제외카드사={profile['excluded_issuer']}"
    )

def candidate_payload(cards: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    payload = []
    for c in cards:
        payload.append({
            "card_name": c["card_name"],
            "issuer": c["issuer"],
            "card_type": c["card_type"],
            "annual_fee": c["annual_fee"],
            "min_spend": c["min_spend"],
            "benefits": c["benefits"],
            "description": c["description"][:700],
            "image_url": c["image_url"],
        })
    return payload

def ask_llm_for_top3(profile: Dict[str, Any], candidates: List[Dict[str, Any]]) -> Dict[str, Any]:
    prompt = {
        "task": "사용자에게 가장 적합한 카드 3개를 후보 목록에서만 고른다.",
        "rules": [
            "후보 목록에 없는 카드는 절대 만들지 않는다.",
            "카드명은 후보 카드명과 정확히 동일하게 쓴다.",
            "과장 없이 현실적으로 추천한다.",
            "사용자의 소비패턴과 혜택 연결성을 우선한다.",
            "연회비, 전월실적, 혜택 방향, 사용 편의성을 함께 고려한다."
        ],
        "user_profile": build_profile_summary(profile),
        "candidate_cards": candidate_payload(candidates),
        "output_format": {
            "intro_message": "추천 전체 소개 2~4문장",
            "recommendations": [
                {
                    "card_name": "후보 카드명 그대로",
                    "summary": "한 줄 요약",
                    "reason": "추천 이유 2~4문장",
                    "pros": ["장점1", "장점2"],
                    "caution": "주의점 1문장"
                }
            ]
        }
    }

    try:
        resp = client.responses.create(
            model="gpt-5.4",
            input=[
                {
                    "role": "system",
                    "content": (
                        "너는 카드 추천 전문가다. "
                        "반드시 유효한 JSON만 출력한다. "
                        "코드블록, 마크다운, 설명문을 추가하지 않는다."
                    )
                },
                {
                    "role": "user",
                    "content": json.dumps(prompt, ensure_ascii=False)
                }
            ]
        )
        return json.loads(resp.output_text.strip())
    except Exception:
        top3 = candidates[:3]
        return {
            "intro_message": "입력하신 조건과 소비 패턴을 기준으로 현재 후보 중에서 가장 잘 맞는 카드 3개를 골랐어요.",
            "recommendations": [
                {
                    "card_name": c["card_name"],
                    "summary": "현재 조건에 비교적 잘 맞는 카드예요.",
                    "reason": f"{', '.join(c['benefits'][:3]) if c['benefits'] else '생활형'} 혜택이 현재 소비 패턴과 연결돼 활용하기 좋아요.",
                    "pros": c["benefits"][:2] if c["benefits"] else ["무난한 활용도", "주요 생활 혜택"],
                    "caution": "세부 혜택 조건과 실적 기준은 카드사 안내를 함께 확인해보세요."
                }
                for c in top3
            ]
        }

def run_recommendation_pipeline(profile: Dict[str, Any], all_cards: List[Dict[str, Any]]) -> Dict[str, Any]:
    hard_filtered = hard_filter_cards(all_cards, profile)

    if not hard_filtered:
        return {
            "intro_message": "현재 조건에 맞는 카드 후보가 너무 적거나 없어요. 연회비나 카드 종류 조건을 조금 완화해보는 게 좋아요.",
            "items": [],
            "candidate_count": 0
        }

    reduced = soft_rank_cards(hard_filtered, profile, top_k=25)
    llm_result = ask_llm_for_top3(profile, reduced)

    name_map = {c["card_name"]: c for c in reduced}
    final_items = []
    for item in llm_result.get("recommendations", [])[:3]:
        name = item.get("card_name")
        if name in name_map:
            final_items.append({**name_map[name], **item})

    if not final_items:
        for c in reduced[:3]:
            final_items.append({
                **c,
                "summary": "현재 조건에 비교적 잘 맞는 카드예요.",
                "reason": f"{', '.join(c['benefits'][:3]) if c['benefits'] else '생활형'} 혜택이 현재 소비 패턴과 연결돼 있어요.",
                "pros": c["benefits"][:2] if c["benefits"] else ["활용도 높음", "무난한 혜택"],
                "caution": "세부 조건은 카드사 안내를 확인해보세요."
            })

    return {
        "intro_message": llm_result.get("intro_message", "후보를 좁힌 뒤 가장 잘 맞는 카드 3개를 골랐어요."),
        "items": final_items,
        "candidate_count": len(reduced)
    }

# =========================================================
# 데이터 로드
# =========================================================
if not st.session_state.all_cards:
    st.session_state.all_cards = load_all_cards()

# =========================================================
# 사이드바
# =========================================================
with st.sidebar:
    st.title("💳 추천 조건 설정")
    st.caption("1200개 전체를 바로 넣지 않고, 먼저 후보를 줄인 뒤 추천해요.")

    p = st.session_state.user_profile

    card_type = st.selectbox("카드 종류", CARD_TYPE_OPTIONS, index=CARD_TYPE_OPTIONS.index(p["card_type"]))
    monthly_spend = st.selectbox("월 평균 소비금액", SPEND_OPTIONS, index=SPEND_OPTIONS.index(p["monthly_spend"]))
    annual_fee_limit = st.selectbox("연회비 허용 범위", FEE_OPTIONS, index=FEE_OPTIONS.index(p["annual_fee_limit"]))
    main_goal = st.selectbox("추천 목적", GOAL_OPTIONS, index=GOAL_OPTIONS.index(p["main_goal"]))
    lifestyle = st.selectbox("라이프스타일", LIFESTYLE_OPTIONS, index=LIFESTYLE_OPTIONS.index(p["lifestyle"]))

    st.markdown("### 주요 소비 카테고리")
    top_category_1 = st.selectbox("1순위 소비", CATEGORY_OPTIONS[:-1], index=CATEGORY_OPTIONS[:-1].index(p["top_category_1"]))
    top_category_2 = st.selectbox("2순위 소비", CATEGORY_OPTIONS, index=CATEGORY_OPTIONS.index(p["top_category_2"]))
    top_category_3 = st.selectbox("3순위 소비", CATEGORY_OPTIONS, index=CATEGORY_OPTIONS.index(p["top_category_3"]))

    st.markdown("### 추가 조건")
    performance_preference = st.selectbox("전월실적 선호", PERFORMANCE_OPTIONS, index=PERFORMANCE_OPTIONS.index(p["performance_preference"]))
    benefit_style = st.selectbox("혜택 조건 선호", SIMPLE_OPTIONS, index=SIMPLE_OPTIONS.index(p["benefit_style"]))
    preferred_issuer = st.selectbox("선호 카드사", ISSUER_OPTIONS, index=ISSUER_OPTIONS.index(p["preferred_issuer"]))
    excluded_issuer = st.selectbox("제외 카드사", ISSUER_OPTIONS, index=ISSUER_OPTIONS.index(p["excluded_issuer"]))

    col_a, col_b = st.columns(2)
    with col_a:
        start_btn = st.button("추천 시작", use_container_width=True)
    with col_b:
        reset_btn = st.button("초기화", use_container_width=True)

# =========================================================
# 초기화
# =========================================================
if reset_btn:
    for k in list(st.session_state.keys()):
        del st.session_state[k]
    st.rerun()

# =========================================================
# 추천 시작
# =========================================================
if start_btn:
    st.session_state.user_profile = {
        "card_type": card_type,
        "monthly_spend": monthly_spend,
        "annual_fee_limit": annual_fee_limit,
        "main_goal": main_goal,
        "lifestyle": lifestyle,
        "top_category_1": top_category_1,
        "top_category_2": top_category_2,
        "top_category_3": top_category_3,
        "performance_preference": performance_preference,
        "benefit_style": benefit_style,
        "preferred_issuer": preferred_issuer,
        "excluded_issuer": excluded_issuer,
    }

    st.session_state.started = True

    top_categories = ", ".join(get_top_categories(st.session_state.user_profile))
    add_message(
        "assistant",
        f"좋아요. {card_type}, 월 소비 {monthly_spend}, 연회비 {annual_fee_limit}, 주요 소비 {top_categories}, 목표는 {main_goal} 기준으로 먼저 후보를 줄여볼게요."
    )

    with st.spinner("카드 후보를 줄이고 추천 이유를 정리하는 중이에요..."):
        result = run_recommendation_pipeline(
            st.session_state.user_profile,
            st.session_state.all_cards
        )
        st.session_state.recommendations = result["items"]
        st.session_state.candidate_cards = result["candidate_count"]
        add_message("assistant", result["intro_message"])

    st.rerun()

# =========================================================
# 메인 레이아웃
# =========================================================
left, right = st.columns([2.2, 1])

with left:
    st.markdown('<div class="title">AI 카드 추천 챗봇</div>', unsafe_allow_html=True)
    st.markdown('<div class="subtitle">후보를 먼저 줄인 뒤, 그 안에서 가장 잘 맞는 카드 3개를 추천합니다.</div>', unsafe_allow_html=True)

    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.write(msg["content"])

    if st.session_state.started:
        user_text = st.chat_input("예: 연회비 낮은 쪽으로 다시 추천해줘")
        if user_text:
            add_message("user", user_text)

            # 간단 후속 반영
            if "체크카드" in user_text:
                st.session_state.user_profile["card_type"] = "체크카드"
                add_message("assistant", "좋아요. 체크카드 기준으로 다시 후보를 줄여볼게요.")
            elif "신용카드" in user_text:
                st.session_state.user_profile["card_type"] = "신용카드"
                add_message("assistant", "좋아요. 신용카드 기준으로 다시 볼게요.")
            elif "연회비" in user_text and ("낮" in user_text or "싼" in user_text):
                st.session_state.user_profile["annual_fee_limit"] = "1만원 이하"
                add_message("assistant", "좋아요. 연회비 부담이 낮은 카드 위주로 다시 볼게요.")
            elif "전월실적" in user_text and ("없" in user_text or "싫" in user_text):
                st.session_state.user_profile["performance_preference"] = "전월실적 없는 카드 선호"
                add_message("assistant", "좋아요. 전월실적 없는 카드 위주로 다시 좁혀볼게요.")
            elif "카페" in user_text:
                st.session_state.user_profile["top_category_1"] = "카페"
                add_message("assistant", "좋아요. 카페 혜택을 더 강하게 반영할게요.")
            elif "교통" in user_text:
                st.session_state.user_profile["top_category_1"] = "대중교통"
                add_message("assistant", "좋아요. 교통 혜택을 더 중요하게 볼게요.")
            elif "배달" in user_text:
                st.session_state.user_profile["top_category_1"] = "배달"
                add_message("assistant", "좋아요. 배달 혜택을 더 중요하게 반영할게요.")
            elif "적립" in user_text or "포인트" in user_text:
                st.session_state.user_profile["main_goal"] = "포인트/적립 위주"
                add_message("assistant", "좋아요. 적립형 성격이 강한 카드 쪽으로 다시 볼게요.")
            elif "할인" in user_text:
                st.session_state.user_profile["main_goal"] = "할인 많이 받기"
                add_message("assistant", "좋아요. 할인 중심 카드로 다시 후보를 줄일게요.")
            else:
                add_message("assistant", "말씀하신 조건을 반영해서 다시 추천해볼게요.")

            with st.spinner("조건을 반영해서 다시 추천하는 중이에요..."):
                result = run_recommendation_pipeline(
                    st.session_state.user_profile,
                    st.session_state.all_cards
                )
                st.session_state.recommendations = result["items"]
                st.session_state.candidate_cards = result["candidate_count"]
                add_message("assistant", result["intro_message"])

            st.rerun()

with right:
    st.subheader("현재 조건 요약")
    p = st.session_state.user_profile
    top_categories = ", ".join(get_top_categories(p)) or "미선택"

    st.markdown(f"""
    <div class="info-box"><b>카드 종류</b><br>{p['card_type']}</div>
    <div class="info-box"><b>월 소비금액</b><br>{p['monthly_spend']}</div>
    <div class="info-box"><b>연회비 허용 범위</b><br>{p['annual_fee_limit']}</div>
    <div class="info-box"><b>주요 소비 카테고리</b><br>{top_categories}</div>
    <div class="info-box"><b>추천 목적</b><br>{p['main_goal']}</div>
    <div class="info-box"><b>라이프스타일</b><br>{p['lifestyle']}</div>
    <div class="info-box"><b>전월실적 선호</b><br>{p['performance_preference']}</div>
    <div class="info-box"><b>혜택 조건 선호</b><br>{p['benefit_style']}</div>
    <div class="info-box"><b>선호 카드사</b><br>{p['preferred_issuer']}</div>
    <div class="info-box"><b>제외 카드사</b><br>{p['excluded_issuer']}</div>
    """, unsafe_allow_html=True)

    if st.session_state.started:
        st.markdown(f"""
        <div class="info-box">
            <b>최종 추천 전 후보 수</b><br>{st.session_state.candidate_cards}개
        </div>
        """, unsafe_allow_html=True)

# =========================================================
# 추천 결과
# =========================================================
if st.session_state.recommendations:
    st.markdown("---")
    st.subheader("추천 카드 3개")

    cols = st.columns(3)

    for idx, item in enumerate(st.session_state.recommendations[:3]):
        with cols[idx]:
            st.markdown('<div class="card-box">', unsafe_allow_html=True)

            if item.get("image_url"):
                st.image(item["image_url"], use_container_width=True)

            st.markdown(f"### {item['card_name']}")
            st.caption(item.get("issuer", "카드사 정보 없음"))

            st.markdown(
                f"**연회비** · {item.get('annual_fee', 0):,}원  \n"
                f"**전월실적** · {item.get('min_spend', 0):,}원"
            )

            if item.get("benefits"):
                badges = "".join([f"<span class='badge'>{b}</span>" for b in item["benefits"][:5]])
                st.markdown(badges, unsafe_allow_html=True)

            st.markdown(f"**한줄 요약**  \n{item.get('summary', '-')}")
            st.markdown(f"**추천 이유**  \n{item.get('reason', '-')}")

            pros = item.get("pros", [])
            if pros:
                st.markdown("**장점 포인트**")
                for ptxt in pros[:3]:
                    st.write(f"- {ptxt}")

            caution = item.get("caution")
            if caution:
                st.markdown(f"**주의할 점**  \n{caution}")

            with st.expander("카드 데이터 자세히 보기"):
                st.write("혜택 카테고리:", item.get("benefits", []))
                if item.get("benefit_detail"):
                    st.json(item["benefit_detail"])
                elif item.get("description"):
                    st.write(item["description"])
                else:
                    st.write("추가 설명 데이터가 없습니다.")

            st.markdown("</div>", unsafe_allow_html=True)
