import os
from dotenv import load_dotenv

from langchain_core.documents import Document
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_community.vectorstores import Chroma
from langchain_community.retrievers import BM25Retriever
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser
from langchain_community.chat_message_histories import ChatMessageHistory
from langchain_core.runnables.history import RunnableWithMessageHistory

# 1. 환경 설정 및 데이터 로드
load_dotenv()
MY_API_KEY = os.getenv("OPENAI_API_KEY")

embeddings = OpenAIEmbeddings(
    api_key=MY_API_KEY,
    model="text-embedding-3-small"
)

# 벡터 DB 로드
vector_db = Chroma(
    persist_directory="./card_semantic_db_v3",
    embedding_function=embeddings
)

# BM25용 문서 복구 및 리트리버 설정
all_data = vector_db.get()
documents = [
    Document(page_content=doc, metadata=meta)
    for doc, meta in zip(all_data["documents"], all_data["metadatas"])
]

bm25_retriever = BM25Retriever.from_documents(documents)
bm25_retriever.k = 10
vector_retriever = vector_db.as_retriever(search_kwargs={"k": 10})

# 메타데이터('rank')를 이용해 파이썬 딕셔너리를 자체 생성
all_cards_from_db = {}
for doc in documents:
    name = doc.metadata.get("card_name")
    rank = doc.metadata.get("rank", 999)
    card_type = doc.metadata.get("card_type", "")

    if name and name not in all_cards_from_db:
        all_cards_from_db[name] = {
            "Card_Name": name,
            "Rank": rank,
            "Card_Type": card_type
        }


# ---------------------------------------------------
# 유틸 함수
# ---------------------------------------------------
def get_image_url(metadata: dict) -> str:
    """
    DB 메타데이터에서 이미지 URL 후보 키를 순서대로 확인.
    """
    for key in ["image_url", "Image_URL", "img_url", "card_image_url", "image"]:
        value = metadata.get(key)
        if value and str(value).strip():
            return str(value).strip()
    return ""


def summarize_benefit(text: str, max_len: int = 180) -> str:
    """
    UI 카드용 짧은 혜택 요약.
    """
    if not text:
        return "혜택 정보 없음"

    text = text.strip().replace("\n", " ")
    return text[:max_len] + "..." if len(text) > max_len else text


# ---------------------------------------------------
# 2. 검색 고도화 로직 (하이브리드 + 리랭킹)
# ---------------------------------------------------
def rerank_by_popularity(docs):
    scored_docs = []

    for i, doc in enumerate(docs):
        base_score = (len(docs) - i) / max(len(docs), 1)

        rank_val = doc.metadata.get("rank", 999)

        if isinstance(rank_val, int) and rank_val <= 150:
            popularity_boost = 5.0 + (151 - rank_val) * 0.1
        else:
            popularity_boost = 0.0

        scored_docs.append((doc, base_score + popularity_boost))

    scored_docs.sort(key=lambda x: x[1], reverse=True)
    return [d[0] for d in scored_docs[:10]]


def advanced_retriever_with_rerank(query):
    # 1. 질문 의도 파악 (10대 여부 확인)
    is_teenager = any(
        keyword in query
        for keyword in ["10대", "청소년", "학생", "중학생", "고등학생", "미성년자"]
    )

    # 2. 검색기 세팅
    if is_teenager:
        vector_retriever.search_kwargs = {"k": 10, "filter": {"card_type": "체크카드"}}
        bm25_retriever.k = 10
    else:
        vector_retriever.search_kwargs = {"k": 10}
        bm25_retriever.k = 10

    # 3. 실제 검색 실행
    bm_docs = bm25_retriever.invoke(query)
    vc_docs = vector_retriever.invoke(query)
    combined_docs = bm_docs + vc_docs

    # 4. 중복 제거 및 사후 필터링
    unique_docs = []
    seen_card_names = set()

    for d in combined_docs:
        card_name = d.metadata.get("card_name")
        card_type = str(d.metadata.get("card_type", ""))

        if is_teenager and "신용" in card_type:
            continue

        if card_name and card_name not in seen_card_names:
            unique_docs.append(d)
            seen_card_names.add(card_name)

    # 5. 인기 카드 강제 주입 로직
    if any(keyword in query for keyword in ["인기", "많이 쓰는", "순위", "1위", "대세"]):
        if is_teenager:
            candidate_cards = [
                c for c in all_cards_from_db.values()
                if c["Card_Type"] == "체크카드"
            ]
        else:
            candidate_cards = list(all_cards_from_db.values())

        top_5_cards = sorted(candidate_cards, key=lambda x: x["Rank"])[:5]
        top_5_names = [c["Card_Name"] for c in top_5_cards]

        for doc in documents:
            if doc.metadata.get("card_name") in top_5_names:
                if doc.metadata.get("card_name") not in seen_card_names:
                    unique_docs.append(doc)
                    seen_card_names.add(doc.metadata.get("card_name"))

    # 6. 리랭킹 적용
    return rerank_by_popularity(unique_docs)[:3]


def format_docs(docs):
    """
    LLM에 전달할 Context 문자열 생성.
    이미지 URL까지 함께 넣어서 모델이 답변에 활용할 수 있게 함.
    """
    formatted = []

    for idx, d in enumerate(docs):
        fee = d.metadata.get("annual_fee", "정보없음")
        perf = d.metadata.get("performance", "정보없음")
        image_url = get_image_url(d.metadata)

        # 너무 길면 context 초과될 수 있어서 혜택 본문 길이 제한
        benefit_text = d.page_content[:350]

        doc_text = (
            f"[[🔥 추천 {idx+1}순위 문서 🔥]]\n"
            f"### {d.metadata.get('card_name')} ###\n"
            f"[혜택] {benefit_text}\n"
            f"[조건] 연회비: {fee} / 전월실적: {perf}\n"
            f"[이미지URL] {image_url}"
        )
        formatted.append(doc_text)

    return "\n\n".join(formatted)


# ---------------------------------------------------
# 3. 프롬프트 및 체인 설정
# ---------------------------------------------------
llm = ChatOpenAI(
    model_name="gpt-3.5-turbo",
    api_key=MY_API_KEY,
    temperature=0.1
)

system_prompt = """당신은 대한민국 최고의 '신용/체크카드 맞춤형 추천 전문가(Financial Advisor)'입니다.
반드시 제공된 [카드 혜택 정보(Context)]만을 바탕으로 사용자의 질문에 가장 적합한 카드를 추천하세요.

[제약 조건 (Strict Rules)]
1. 정보의 절대성 (No Hallucination): [Context]에 명시되지 않은 혜택, 연회비, 실적 조건, 이미지 URL은 절대 지어내지 마세요.
2. 사용자 니즈 정밀 매칭: 사용자의 질문과 가장 관련성이 높은 혜택을 가진 카드를 우선 추천하고, 해당 혜택의 구체적인 수치(%, 원)를 반드시 포함하세요.
3. 조건 교차 검증: 혜택 본문 내용에 적힌 실적 조건이 하단의 [조건] 메타데이터보다 우선합니다.
4. 사용자가 특정 개수를 지정하지 않아도 가장 적합한 카드 3개를 추천하세요.
5. 각 추천 카드마다 이미지 URL도 함께 제시하세요. Context의 [이미지URL] 값을 그대로 사용하세요.

[출력 형식 (Output Format)]
### 💳 [카드명]
* **핵심 혜택:** ...
* **연회비:** ... / **전월실적:** ...
* **이미지URL:** ...
* **추천 이유:** ...

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
        context=lambda x: format_docs(advanced_retriever_with_rerank(x["question"]))
    )
    | base_prompt
    | llm
    | StrOutputParser()
)

# 4. 메모리(History) 설정
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


# ---------------------------------------------------
# 5. UI용 카드 데이터 반환 함수
# ---------------------------------------------------
def get_recommendation_cards(question: str):
    """
    Streamlit 카드형 UI에 바로 쓸 수 있는 추천 카드 3개 반환
    """
    docs = advanced_retriever_with_rerank(question)
    cards = []

    for d in docs[:3]:
        cards.append({
            "card_name": d.metadata.get("card_name", "이름 없음"),
            "annual_fee": d.metadata.get("annual_fee", "정보없음"),
            "performance": d.metadata.get("performance", "정보없음"),
            "image_url": get_image_url(d.metadata),
            "benefit_summary": summarize_benefit(d.page_content, 180),
        })

    return cards


# ---------------------------------------------------
# 6. 실행부
# ---------------------------------------------------
if __name__ == "__main__":
    config = {"configurable": {"session_id": "card_expert_session"}}

    print("👤 질문: 인기있는 카드 3개 추천해줘")
    res = conversational_chain.invoke(
        {"question": "인기있는 카드 3개 추천해줘"},
        config=config
    )
    print(f"🤖 응답:\n{res}\n")

    print("📦 UI 카드 데이터:")
    print(get_recommendation_cards("인기있는 카드 3개 추천해줘"))
