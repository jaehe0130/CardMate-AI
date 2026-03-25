import os
from dotenv import load_dotenv

from langchain_openai import ChatOpenAI
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_community.chat_message_histories import ChatMessageHistory
from langchain_core.runnables.history import RunnableWithMessageHistory

from recommender import load_vector_db
from utils import format_docs

load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# 1. Vector DB / Retriever
vector_db = load_vector_db()
retriever = vector_db.as_retriever(search_kwargs={"k": 3})

# 2. LLM
llm = ChatOpenAI(
    model="gpt-4o-mini",
    api_key=OPENAI_API_KEY,
    temperature=0.2
)

# 3. Prompt
system_prompt = """당신은 대한민국 카드 추천 및 혜택 안내를 도와주는 금융 챗봇입니다.
사용자의 질문과 제공된 [카드 혜택 정보(Context)]만 바탕으로 정확하게 답변하세요.

[답변 규칙]
1. 반드시 Context 안에 있는 정보만 사용하세요.
2. 정보가 불충분하면 추측하지 말고, "제공된 카드 정보만으로는 확인이 어렵습니다."라고 답하세요.
3. 사용자가 잘못된 정보를 말해도 그대로 동조하지 말고, Context 기준으로 정정하세요.
4. 답변은 친절하고 간결하게 작성하세요.
5. 카드명, 연회비, 전월실적, 핵심 혜택이 있으면 우선적으로 정리하세요.
6. 추천 요청이면 최대 3개 카드까지 정리하세요.
7. 마크다운 글머리표를 사용해 깔끔하게 보여주세요.

[카드 혜택 정보(Context)]
{context}
"""

prompt = ChatPromptTemplate.from_messages([
    ("system", system_prompt),
    MessagesPlaceholder(variable_name="history"),
    ("human", "{question}")
])

# 4. 기본 체인
base_chain = (
    RunnablePassthrough.assign(
        context=lambda x: format_docs(retriever.invoke(x["question"]))
    )
    | prompt
    | llm
    | StrOutputParser()
)

# 5. 메모리 저장소
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
    session_id = "test_room"

    q1 = "연회비 낮고 카페 혜택 좋은 카드 추천해줘"
    print("Q1:", q1)
    print(ask_card_chatbot(q1, session_id=session_id))
    print("-" * 50)

    q2 = "그중에서 전월실적 조건이 가장 낮은 건 뭐야?"
    print("Q2:", q2)
    print(ask_card_chatbot(q2, session_id=session_id))
