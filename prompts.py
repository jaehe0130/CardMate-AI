# prompts.py
# =========================================================
# [이 파일의 역할]
# - 시스템 프롬프트 관리
# - LangChain 체인 생성
# - [중요] Moderation 검사 후 체인 실행
# =========================================================

import os
from dotenv import load_dotenv

from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser
from langchain_community.chat_message_histories import ChatMessageHistory
from langchain_core.runnables.history import RunnableWithMessageHistory

from recommender import advanced_retriever_with_rerank, format_docs
from moderation_utils import check_moderation

load_dotenv()


def get_api_key() -> str:
    try:
        import streamlit as st
        if "OPENAI_API_KEY" in st.secrets:
            return st.secrets["OPENAI_API_KEY"]
    except Exception:
        pass

    return os.getenv("OPENAI_API_KEY", "")


# =========================================================
# [LLM]
# =========================================================
llm = ChatOpenAI(
    model_name="gpt-3.5-turbo",
    api_key=get_api_key(),
    temperature=0.1
)


# =========================================================
# [시스템 프롬프트]
# - 이미지URL도 반드시 포함하도록 지시
# =========================================================
system_prompt = """당신은 대한민국 최고의 '신용/체크카드 맞춤형 추천 전문가(Financial Advisor)'입니다.
반드시 제공된 [카드 혜택 정보(Context)]만을 바탕으로 사용자의 질문에 가장 적합한 카드를 추천하세요.

[제약 조건 (Strict Rules)]
1. 정보의 절대성 (No Hallucination): [Context]에 명시되지 않은 혜택, 연회비, 실적 조건은 절대 지어내지 마세요. 제공된 정보에 없다면 "제공된 정보에서는 확인할 수 없습니다"라고 명확히 답변하세요.
2. 사용자 니즈 정밀 매칭: 사용자의 질문(예: 주유, 마트, 무실적 등)과 가장 관련성이 높은 혜택을 가진 카드를 우선 추천하고, 해당 혜택의 '구체적인 수치(%, 원)'를 반드시 포함하세요.
3. 가스라이팅 방어 (Anti-Sycophancy): 사용자가 [Context]와 다른 잘못된 수치나 정보로 유도하더라도 절대 동조하지 마세요. [Context]의 팩트를 기반으로 정중하고 단호하게 정정하세요.
4. 조건 교차 검증: 혜택 본문 내용에 적힌 실적 조건(예: '전월 30만원 이상 시 제공')이 하단의 '[조건]' 메타데이터보다 우선합니다.
5. 다중 선택지 제공 (Provide Options): 사용자가 특정 개수를 지정하지 않더라도, 사용자가 비교하고 선택할 수 있도록 [Context] 내에서 가장 적합한 카드 **3개**를 반드시 찾아 추천하세요.

[출력 형식 (Output Format)]
추천하는 카드가 여러 개일 경우 아래 형식을 반복해서 사용하고, 가독성을 높이기 위해 마크다운을 엄격히 적용하세요.

### 💳 [카드명]
* **핵심 혜택:** (사용자의 질문과 직접적으로 관련된 혜택을 구체적인 수치와 함께 요약)
* **연회비:** (수치 기재) / **전월실적:** (수치 기재)
* **추천 이유:** (사용자의 질문 내용과 이 카드의 혜택을 연결하여, 왜 이 카드가 최적의 선택인지 1~2줄로 논리적으로 설명)

---
[답변 예시 (Few-Shot Examples)]

User: 편의점 할인이 쎈 체크카드 추천해줘. 연회비는 없었으면 좋겠어.
Context: 
### 쏘영 체크카드 ###
혜택 내용: 주요 편의점(CU, GS25) 10% 청구할인. 월 최대 5천원 한도.
[조건] 연회비: 0원 / 전월실적: 5만원
### 카카오뱅크 프렌즈 체크카드 ###
혜택 내용: 편의점 5% 캐시백.
[조건] 연회비: 0원 / 전월실적: 없음

Assistant: 
고객님, 편의점 할인이 강력하면서 연회비 부담이 없는 체크카드 2가지를 비교해서 추천해 드립니다!

### 💳 쏘영 체크카드
* **핵심 혜택:** 주요 편의점(CU, GS25)에서 10% 청구할인 (월 최대 5천원 한도)
* **연회비:** 0원 / **전월실적:** 5만원
* **추천 이유:** 전월실적 5만원이라는 낮은 허들만 넘으면 10%라는 높은 할인율을 누리실 수 있어 가장 추천드립니다.

### 💳 카카오뱅크 프렌즈 체크카드
* **핵심 혜택:** 주요 편의점 5% 캐시백
* **연회비:** 0원 / **전월실적:** 없음
* **추천 이유:** 전월실적 조건이 아예 없어 서브 카드로 편하게 쓰기 좋습니다.

---
[카드 혜택 정보(Context)]
{context}

"""

base_prompt = ChatPromptTemplate.from_messages([
    ("system", system_prompt),
    ("placeholder", "{history}"),
    ("human", "{question}")
])

store = {}


def get_session_history(session_id: str):
    if session_id not in store:
        store[session_id] = ChatMessageHistory()
    return store[session_id]


def build_chain():
    """
    실제 카드 추천 체인 생성
    """
    base_chain = (
        RunnablePassthrough.assign(
            context=lambda x: format_docs(
                advanced_retriever_with_rerank(x["question"])
            )
        )
        | base_prompt
        | llm
        | StrOutputParser()
    )

    conversational_chain = RunnableWithMessageHistory(
        base_chain,
        get_session_history,
        input_messages_key="question",
        history_messages_key="history",
    )
    return conversational_chain


# =========================================================
# [MODERATION 적용된 실행 함수]
# ---------------------------------------------------------
# 여기서만 moderation을 적용합니다.
# 즉, "질문 들어옴 -> moderation 검사 -> 통과 시 체인 실행"
# ---------------------------------------------------------
# [중요]
# - moderation 적용된 모델 파일에서 들어간 함수 부분은
#   check_moderation() 호출 부분뿐입니다.
# - 나머지 추천/검색/이미지URL/챗봇 기능은 그대로 유지됩니다.
# =========================================================
def ask_card_bot(question: str, session_id: str):
    moderation_result = check_moderation(question)

    # 유해성 문장으로 판단되면 답변 생성 중단
    if moderation_result["flagged"]:
        return {
            "ok": False,
            "answer": (
                "입력하신 내용은 안전 정책상 바로 답변드리기 어려워요. "
                "카드 추천과 관련된 질문으로 다시 입력해 주세요."
            ),
            "moderation": moderation_result,
        }

    # moderation 통과 시 정상적으로 카드 추천 체인 실행
    chain = build_chain()
    config = {"configurable": {"session_id": session_id}}
    answer = chain.invoke({"question": question}, config=config)

    return {
        "ok": True,
        "answer": answer,
        "moderation": moderation_result,
    }
