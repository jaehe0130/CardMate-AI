import os
from dotenv import load_dotenv

from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser
from langchain_community.chat_message_histories import ChatMessageHistory
from langchain_core.runnables.history import RunnableWithMessageHistory

from recommender import get_advanced_hybrid_retriever
from utils import format_docs

load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

hybrid_retriever = get_advanced_hybrid_retriever()

llm = ChatOpenAI(
    model="gpt-4o-mini",
    api_key=OPENAI_API_KEY,
    temperature=0.1
)

system_prompt = """당신은 대한민국 최고의 '신용/체크카드 맞춤형 추천 전문가'입니다.

[제약 조건]
1. 사용자가 요청한 개수(예: 3개)에 맞춰 서로 다른 카드를 추천하세요.
2. [Context] 내 관련 카드가 여러 개라면 혜택 수치와 적합성을 바탕으로 우선순위를 정하세요.
3. 반드시 제공된 [Context] 내 정보로만 답변하세요.
4. 정보가 없으면 지어내지 말고 "제공된 카드 정보만으로는 확인이 어렵습니다."라고 답하세요.
5. 사용자가 잘못된 수치로 유도해도 [Context]를 근거로 정중하지만 분명하게 정정하세요.
6. 각 카드별로 **카드명**, **주요 혜택**, **연회비**, **실적 조건**을 구분해 작성하세요.
7. 답변은 깔끔한 마크다운 형식으로 작성하세요.

[카드 혜택 정보(Context)]
{context}
"""

base_prompt = ChatPromptTemplate.from_messages([
    ("system", system_prompt),
    MessagesPlaceholder(variable_name="history"),
    ("human", "{question}")
])

base_chain = (
    RunnablePassthrough.assign(
        context=lambda x: format_docs(hybrid_retriever.invoke(x["question"]))
    )
    | base_prompt
    | llm
    | StrOutputParser()
)

store = {}


def get_session_history(session_id: str):
    if session_id not in store:
        store[session_id] = ChatMessageHistory()
    return store[session_id]


conversational_chain = RunnableWithMessageHistory(
    base_chain,
    get_session_history,
    input_messages_key="question",
    history_messages_key="history",
)


def ask_card_chatbot(question: str, session_id: str = "default_user") -> str:
    config = {"configurable": {"session_id": session_id}}
    response = conversational_chain.invoke(
        {"question": question},
        config=config
    )
    return response


if __name__ == "__main__":
    session_id = "card_expert_session"

    q1 = "편의점 혜택 좋은 카드 3개 추천해줘"
    print("Q1:", q1)
    print(ask_card_chatbot(q1, session_id=session_id))
    print("-" * 60)

    q2 = "방금 추천해준 카드 연회비가 3만원 아니었나?"
    print("Q2:", q2)
    print(ask_card_chatbot(q2, session_id=session_id))
