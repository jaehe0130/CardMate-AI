import streamlit as st
import json
from pathlib import Path

st.set_page_config(
    page_title="카드 추천 챗봇",
    page_icon="💳",
    layout="wide"
)

# -----------------------------
# 기본 스타일
# -----------------------------
st.markdown("""
<style>
.block-container {
    padding-top: 1.5rem;
    padding-bottom: 2rem;
    max-width: 1200px;
}
.card-box {
    padding: 1.2rem;
    border-radius: 18px;
    background: #ffffff;
    border: 1px solid #eaeaea;
    box-shadow: 0 4px 16px rgba(0,0,0,0.04);
    margin-bottom: 1rem;
}
.info-box {
    padding: 0.9rem 1rem;
    border-radius: 14px;
    background: #f7f8fa;
    border: 1px solid #edf0f3;
    margin-bottom: 0.8rem;
}
.small-text {
    color: #666;
    font-size: 0.92rem;
}
.badge {
    display: inline-block;
    padding: 0.2rem 0.55rem;
    margin-right: 0.35rem;
    margin-bottom: 0.35rem;
    border-radius: 999px;
    background: #f1f3f5;
    font-size: 0.82rem;
}
</style>
""", unsafe_allow_html=True)

# -----------------------------
# 데이터 로드
# -----------------------------
CARD_PATH = Path("cards.json")

def load_cards():
    if CARD_PATH.exists():
        with open(CARD_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

cards = load_cards()

# -----------------------------
# session_state 초기화
# -----------------------------
def init_session():
    if "user_profile" not in st.session_state:
        st.session_state.user_profile = {
            "card_type": "상관없음",
            "monthly_spend": 500000,
            "annual_fee_limit": 20000,
            "top_categories": [],
            "main_goal": "생활비 절약",
            "lifestyle": "사회초년생",

            # 챗봇이 추가로 알아내는 정보
            "main_vs_sub": None,
            "allow_performance_requirement": None,
            "top_priority_category": None,
            "prefer_discount_or_points": None,
            "commute": None,
            "delivery_heavy": None,
            "online_shopping_heavy": None,
            "preferred_issuers": [],
            "excluded_issuers": [],
            "existing_cards": [],
            "disliked_conditions": []
        }

    if "messages" not in st.session_state:
        st.session_state.messages = [
            {
                "role": "assistant",
                "content": "안녕하세요. 소비 패턴에 맞는 카드를 추천해드릴게요. 왼쪽에서 기본 조건을 입력한 뒤 추천을 시작해보세요."
            }
        ]

    if "started" not in st.session_state:
        st.session_state.started = False

    if "recommendations" not in st.session_state:
        st.session_state.recommendations = []

    if "question_step" not in st.session_state:
        st.session_state.question_step = 0

    if "waiting_for_answer" not in st.session_state:
        st.session_state.waiting_for_answer = False

init_session()

# -----------------------------
# 질문 플로우
# -----------------------------
QUESTION_FLOW = [
    {
        "key": "main_vs_sub",
        "question": "이번 카드는 메인카드로 쓰실 예정인가요, 아니면 서브카드로 찾고 계신가요?",
        "type": "choice",
        "options": ["메인카드", "서브카드"]
    },
    {
        "key": "allow_performance_requirement",
        "question": "전월실적 조건이 조금 있어도 혜택이 좋으면 괜찮으세요?",
        "type": "choice",
        "options": ["네", "아니요"]
    },
    {
        "key": "top_priority_category",
        "question": "선택하신 소비 항목 중에서 가장 중요한 혜택 하나만 고른다면 무엇인가요?",
        "type": "dynamic_choice"
    },
    {
        "key": "prefer_discount_or_points",
        "question": "할인형과 적립형 중 어떤 쪽을 더 선호하세요?",
        "type": "choice",
        "options": ["할인형", "적립형", "둘 다 괜찮음"]
    }
]

# -----------------------------
# 유틸 함수
# -----------------------------
def add_message(role, content):
    st.session_state.messages.append({"role": role, "content": content})

def format_currency(v):
    return f"{int(v):,}원"

def get_missing_question():
    """
    아직 답하지 않은 질문 중 다음 질문 반환
    """
    for item in QUESTION_FLOW:
        key = item["key"]
        if st.session_state.user_profile.get(key) is None:
            return item
    return None

def convert_answer(key, answer):
    if key == "allow_performance_requirement":
        return True if answer == "네" else False
    return answer

def generate_initial_summary(profile):
    cats = ", ".join(profile["top_categories"]) if profile["top_categories"] else "미선택"
    return (
        f"입력해주신 조건을 정리하면, "
        f"{profile['card_type']} 기준 / 월 소비 {format_currency(profile['monthly_spend'])} / "
        f"연회비 {format_currency(profile['annual_fee_limit'])} 이하 / "
        f"주요 소비는 {cats} / 목표는 {profile['main_goal']}이네요. "
        f"조금만 더 여쭤보고 더 잘 맞는 카드로 추천해드릴게요."
    )

# -----------------------------
# 추천 점수 계산
# -----------------------------
def calculate_score(card, user):
    score = 0

    # 카드 종류
    if user["card_type"] != "상관없음":
        if card["card_type"] == user["card_type"]:
            score += 25
        else:
            score -= 50

    # 연회비
    if card["annual_fee"] <= user["annual_fee_limit"]:
        score += 20
    else:
        score -= 20

    # 전월 실적
    if user["allow_performance_requirement"] is False:
        if card["min_spend"] == 0:
            score += 20
        else:
            score -= 15
    elif user["allow_performance_requirement"] is True:
        if card["min_spend"] <= user["monthly_spend"]:
            score += 10

    # 주요 카테고리 일치
    overlap = set(card["benefits"]) & set(user["top_categories"])
    score += len(overlap) * 12

    # 최우선 카테고리
    if user["top_priority_category"]:
        if user["top_priority_category"] in card["benefits"]:
            score += 20

    # 목표 기반
    tags = card.get("tags", [])

    if user["main_goal"] in ["생활비 절약", "할인 많이 받기"]:
        if "할인형" in tags:
            score += 15
    if user["main_goal"] == "포인트/적립 위주":
        if "적립형" in tags or "포인트" in tags:
            score += 15

    # 할인형/적립형 선호
    if user["prefer_discount_or_points"] == "할인형" and "할인형" in tags:
        score += 15
    if user["prefer_discount_or_points"] == "적립형" and ("적립형" in tags or "포인트" in tags):
        score += 15

    # 라이프스타일
    target = card.get("target", [])
    if user["lifestyle"] in target:
        score += 10

    # 메인/서브카드
    if user["main_vs_sub"] == "메인카드" and "메인카드" in target:
        score += 8
    if user["main_vs_sub"] == "서브카드" and "서브카드" in target:
        score += 8

    return score

def recommend_cards(cards, user, top_n=3):
    scored = []
    for card in cards:
        score = calculate_score(card, user)
        scored.append((card, score))
    scored.sort(key=lambda x: x[1], reverse=True)
    return scored[:top_n]

def build_reason(card, user):
    reasons = []

    overlap = list(set(card["benefits"]) & set(user["top_categories"]))
    if overlap:
        reasons.append(f"주요 소비 항목인 {', '.join(overlap)} 혜택이 포함돼 있어요")

    if user["top_priority_category"] and user["top_priority_category"] in card["benefits"]:
        reasons.append(f"가장 중요하게 본 '{user['top_priority_category']}' 혜택에 잘 맞아요")

    if card["annual_fee"] <= user["annual_fee_limit"]:
        reasons.append(f"연회비도 {format_currency(user['annual_fee_limit'])} 이하로 부담이 비교적 적어요")

    if user["allow_performance_requirement"] is False and card["min_spend"] == 0:
        reasons.append("전월실적 조건이 없어서 쓰기 편해요")
    elif user["allow_performance_requirement"] is True:
        reasons.append("전월실적 조건을 감안해도 혜택 구성이 괜찮은 편이에요")

    tags = card.get("tags", [])
    if user["prefer_discount_or_points"] == "할인형" and "할인형" in tags:
        reasons.append("선호하신 할인형 카드 성격과 잘 맞아요")
    if user["prefer_discount_or_points"] == "적립형" and ("적립형" in tags or "포인트" in tags):
        reasons.append("선호하신 적립형 카드 성격과 잘 맞아요")

    if not reasons:
        reasons.append("입력하신 조건과 전반적으로 잘 맞는 무난한 카드예요")

    return " · ".join(reasons[:3])

# -----------------------------
# UI: 사이드바
# -----------------------------
with st.sidebar:
    st.title("💳 카드 추천 설정")
    st.caption("기본 조건만 먼저 입력하면, 부족한 정보는 챗봇이 이어서 물어봐요.")

    card_type = st.radio(
        "카드 종류",
        ["신용카드", "체크카드", "상관없음"],
        index=["신용카드", "체크카드", "상관없음"].index(st.session_state.user_profile["card_type"])
    )

    monthly_spend = st.slider(
        "월 평균 소비금액",
        min_value=100000,
        max_value=3000000,
        step=100000,
        value=int(st.session_state.user_profile["monthly_spend"])
    )

    annual_fee_limit = st.selectbox(
        "연회비 허용 범위",
        [0, 10000, 20000, 30000, 50000],
        index=[0, 10000, 20000, 30000, 50000].index(st.session_state.user_profile["annual_fee_limit"]),
        format_func=lambda x: "연회비 없음" if x == 0 else f"{x:,}원 이하"
    )

    top_categories = st.multiselect(
        "주요 소비 카테고리",
        ["카페", "대중교통", "배달", "편의점", "통신비", "쇼핑", "주유", "OTT/구독", "여행", "공과금"],
        default=st.session_state.user_profile["top_categories"]
    )

    main_goal = st.selectbox(
        "추천 목적",
        ["생활비 절약", "할인 많이 받기", "포인트/적립 위주", "교통/카페 특화", "배달/편의점 특화", "쇼핑 특화", "여행/마일리지"],
        index=["생활비 절약", "할인 많이 받기", "포인트/적립 위주", "교통/카페 특화", "배달/편의점 특화", "쇼핑 특화", "여행/마일리지"].index(st.session_state.user_profile["main_goal"])
    )

    lifestyle = st.selectbox(
        "라이프스타일",
        ["사회초년생", "직장인", "대학생", "자취생", "프리랜서", "기타"],
        index=["사회초년생", "직장인", "대학생", "자취생", "프리랜서", "기타"].index(st.session_state.user_profile["lifestyle"])
    )

    col_sb1, col_sb2 = st.columns(2)
    with col_sb1:
        start_btn = st.button("추천 시작", use_container_width=True)
    with col_sb2:
        reset_btn = st.button("초기화", use_container_width=True)

# 초기화
if reset_btn:
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    st.rerun()

# 추천 시작
if start_btn:
    st.session_state.user_profile["card_type"] = card_type
    st.session_state.user_profile["monthly_spend"] = monthly_spend
    st.session_state.user_profile["annual_fee_limit"] = annual_fee_limit
    st.session_state.user_profile["top_categories"] = top_categories
    st.session_state.user_profile["main_goal"] = main_goal
    st.session_state.user_profile["lifestyle"] = lifestyle

    st.session_state.started = True
    st.session_state.recommendations = []

    add_message("assistant", generate_initial_summary(st.session_state.user_profile))

    next_q = get_missing_question()
    if next_q:
        add_message("assistant", next_q["question"])
        st.session_state.waiting_for_answer = True
    else:
        st.session_state.waiting_for_answer = False

# -----------------------------
# 메인 레이아웃
# -----------------------------
left, right = st.columns([2.2, 1])

with left:
    st.title("카드 추천 챗봇")
    st.caption("사이드바에서 기본 조건을 선택하고, 챗봇과 짧게 대화하면 더 잘 맞는 카드 3개를 추천해드려요.")

    # 예시 버튼
    ex1, ex2, ex3 = st.columns(3)
    with ex1:
        if st.button("카페 할인 좋은 카드"):
            add_message("user", "카페 할인 좋은 카드 추천해줘")
            add_message("assistant", "좋아요. 카페 혜택을 더 중요하게 반영해서 볼게요. 사이드바에서 소비 카테고리에 카페를 포함하면 더 정확해져요.")
    with ex2:
        if st.button("사회초년생용 카드"):
            add_message("user", "사회초년생용 카드 추천해줘")
            add_message("assistant", "좋아요. 연회비 부담이 낮고 생활 혜택이 많은 카드 위주로 보는 게 좋아요.")
    with ex3:
        if st.button("전월실적 없는 카드"):
            add_message("user", "전월실적 없는 카드 추천해줘")
            st.session_state.user_profile["allow_performance_requirement"] = False
            add_message("assistant", "좋아요. 전월실적 없는 카드에 가점을 주도록 반영했어요.")

    st.markdown("---")

    # 채팅 히스토리
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.write(msg["content"])

    # 챗봇 응답용 입력
    if st.session_state.started and st.session_state.waiting_for_answer:
        current_q = get_missing_question()

        if current_q:
            if current_q["type"] == "choice":
                answer = st.radio(
                    "답변 선택",
                    current_q["options"],
                    key=f"radio_{current_q['key']}"
                )
                if st.button("답변 제출", key=f"submit_{current_q['key']}"):
                    add_message("user", answer)
                    st.session_state.user_profile[current_q["key"]] = convert_answer(current_q["key"], answer)

                    next_q = get_missing_question()
                    if next_q:
                        add_message("assistant", next_q["question"])
                        st.session_state.waiting_for_answer = True
                    else:
                        st.session_state.waiting_for_answer = False
                        recs = recommend_cards(cards, st.session_state.user_profile, top_n=3)
                        st.session_state.recommendations = recs
                        add_message("assistant", "좋아요. 답변을 바탕으로 가장 잘 맞는 카드 3개를 추천해드릴게요.")
                    st.rerun()

            elif current_q["type"] == "dynamic_choice":
                dynamic_options = st.session_state.user_profile["top_categories"][:]
                if not dynamic_options:
                    dynamic_options = ["카페", "대중교통", "배달", "쇼핑"]

                answer = st.radio(
                    "가장 중요한 혜택 선택",
                    dynamic_options,
                    key=f"radio_{current_q['key']}"
                )
                if st.button("답변 제출", key=f"submit_{current_q['key']}"):
                    add_message("user", answer)
                    st.session_state.user_profile[current_q["key"]] = answer

                    next_q = get_missing_question()
                    if next_q:
                        add_message("assistant", next_q["question"])
                        st.session_state.waiting_for_answer = True
                    else:
                        st.session_state.waiting_for_answer = False
                        recs = recommend_cards(cards, st.session_state.user_profile, top_n=3)
                        st.session_state.recommendations = recs
                        add_message("assistant", "좋아요. 답변을 바탕으로 가장 잘 맞는 카드 3개를 추천해드릴게요.")
                    st.rerun()

    # 후속 자유 입력
    if st.session_state.started:
        user_text = st.chat_input("예: 연회비 낮은 쪽으로 다시 추천해줘")
        if user_text:
            add_message("user", user_text)

            # 아주 단순한 후속 룰 기반 처리
            if "연회비" in user_text and ("낮" in user_text or "적" in user_text):
                st.session_state.user_profile["annual_fee_limit"] = min(st.session_state.user_profile["annual_fee_limit"], 10000)
                add_message("assistant", "좋아요. 연회비가 더 낮은 카드 위주로 다시 볼게요.")
            elif "체크카드" in user_text:
                st.session_state.user_profile["card_type"] = "체크카드"
                add_message("assistant", "좋아요. 체크카드 기준으로 다시 추천해드릴게요.")
            elif "신용카드" in user_text:
                st.session_state.user_profile["card_type"] = "신용카드"
                add_message("assistant", "좋아요. 신용카드 기준으로 다시 추천해드릴게요.")
            elif "전월실적 없" in user_text:
                st.session_state.user_profile["allow_performance_requirement"] = False
                add_message("assistant", "좋아요. 전월실적 없는 카드에 우선순위를 높일게요.")
            elif "카페" in user_text:
                st.session_state.user_profile["top_priority_category"] = "카페"
                add_message("assistant", "좋아요. 카페 혜택을 더 중요하게 반영할게요.")
            elif "교통" in user_text:
                st.session_state.user_profile["top_priority_category"] = "대중교통"
                add_message("assistant", "좋아요. 대중교통 혜택을 더 중요하게 반영할게요.")
            elif "배달" in user_text:
                st.session_state.user_profile["top_priority_category"] = "배달"
                add_message("assistant", "좋아요. 배달 혜택을 더 중요하게 반영할게요.")
            elif "적립" in user_text or "포인트" in user_text:
                st.session_state.user_profile["prefer_discount_or_points"] = "적립형"
                add_message("assistant", "좋아요. 적립형 카드 중심으로 다시 볼게요.")
            elif "할인" in user_text:
                st.session_state.user_profile["prefer_discount_or_points"] = "할인형"
                add_message("assistant", "좋아요. 할인형 카드 중심으로 다시 볼게요.")
            else:
                add_message("assistant", "말씀해주신 조건을 반영해서 다시 추천해볼게요.")

            recs = recommend_cards(cards, st.session_state.user_profile, top_n=3)
            st.session_state.recommendations = recs
            st.rerun()

with right:
    st.subheader("현재 조건 요약")

    p = st.session_state.user_profile
    cats = ", ".join(p["top_categories"]) if p["top_categories"] else "미선택"

    st.markdown(f"""
    <div class="info-box">
        <b>카드 종류</b><br>{p['card_type']}
    </div>
    <div class="info-box">
        <b>월 소비금액</b><br>{format_currency(p['monthly_spend'])}
    </div>
    <div class="info-box">
        <b>연회비 허용 범위</b><br>{"연회비 없음" if p['annual_fee_limit'] == 0 else format_currency(p['annual_fee_limit']) + " 이하"}
    </div>
    <div class="info-box">
        <b>주요 소비 카테고리</b><br>{cats}
    </div>
    <div class="info-box">
        <b>추천 목적</b><br>{p['main_goal']}
    </div>
    <div class="info-box">
        <b>라이프스타일</b><br>{p['lifestyle']}
    </div>
    """, unsafe_allow_html=True)

    st.subheader("추가로 파악한 정보")
    extra_map = {
        "main_vs_sub": "메인/서브",
        "allow_performance_requirement": "전월실적 허용",
        "top_priority_category": "최우선 혜택",
        "prefer_discount_or_points": "선호 방식"
    }

    for key, label in extra_map.items():
        value = p.get(key)
        if value is not None:
            if isinstance(value, bool):
                value = "허용" if value else "비허용"
            st.markdown(f"<div class='info-box'><b>{label}</b><br>{value}</div>", unsafe_allow_html=True)

# -----------------------------
# 추천 결과 출력
# -----------------------------
if st.session_state.recommendations:
    st.markdown("---")
    st.subheader("추천 카드 3개")

    col1, col2, col3 = st.columns(3)

    for i, (card, score) in enumerate(st.session_state.recommendations):
        target_col = [col1, col2, col3][i]
        with target_col:
            badges = "".join([f"<span class='badge'>{b}</span>" for b in card.get("benefits", [])[:4]])
            detail_lines = ""
            for k, v in list(card.get("benefit_detail", {}).items())[:3]:
                detail_lines += f"- {k}: {v}\n"

            reason = build_reason(card, st.session_state.user_profile)

            st.markdown(f"""
            <div class="card-box">
                <h4 style="margin-bottom:0.4rem;">{card['card_name']}</h4>
                <div class="small-text" style="margin-bottom:0.5rem;">{card['issuer']}</div>
                <div style="margin-bottom:0.5rem;"><b>연회비</b> · {format_currency(card['annual_fee'])}</div>
                <div style="margin-bottom:0.5rem;"><b>전월실적</b> · {format_currency(card['min_spend'])}</div>
                <div style="margin-bottom:0.6rem;">{badges}</div>
                <div style="margin-bottom:0.6rem;"><b>추천 이유</b><br>{reason}</div>
                <div style="margin-bottom:0.4rem;"><b>적합도 점수</b> · {score}점</div>
            </div>
            """, unsafe_allow_html=True)

            with st.expander("혜택 자세히 보기"):
                st.markdown(detail_lines if detail_lines else "등록된 상세 혜택이 없습니다.")

    # 비교표
    st.markdown("### 카드 비교")
    compare_data = []
    for card, score in st.session_state.recommendations:
        compare_data.append({
            "카드명": card["card_name"],
            "카드사": card["issuer"],
            "연회비": format_currency(card["annual_fee"]),
            "전월실적": format_currency(card["min_spend"]),
            "주요혜택": ", ".join(card["benefits"][:3]),
            "적합도": score
        })
    st.dataframe(compare_data, use_container_width=True)
