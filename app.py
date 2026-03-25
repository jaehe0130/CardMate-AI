import os
import json
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
MY_API_KEY = os.getenv('OPENAI_API_KEY')

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")

embeddings = OpenAIEmbeddings(api_key=MY_API_KEY, model="text-embedding-3-small")

# 벡터 DB 로드
vector_db = Chroma(
    persist_directory=os.path.join(DATA_DIR, "card_semantic_db"),
    embedding_function=embeddings
)

# BM25용 문서 복구 및 리트리버 설정
all_data = vector_db.get()
documents = [
    Document(page_content=doc, metadata=meta) 
    for doc, meta in zip(all_data['documents'], all_data['metadatas'])
]

bm25_retriever = BM25Retriever.from_documents(documents)
bm25_retriever.k = 10
vector_retriever = vector_db.as_retriever(search_kwargs={"k": 10})

# 인기 카드 데이터 로드 (리랭킹용)
def load_top_card_dict(filepath):
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return { (item.get('Card_Company'), item.get('Card_Name'), item.get('Card_Type')): item for item in data }
    except:
        return {}

top_info_dict = load_top_card_dict(os.path.join(DATA_DIR, 'top_card_data.json'))

# 2. 검색 고도화 로직 (하이브리드 + 리랭킹)
def rerank_by_popularity(docs):
    scored_docs = []
    for i, doc in enumerate(docs):
        meta = doc.metadata
        card_key = (meta.get('card_company'), meta.get('card_name'), meta.get('card_type'))
        
        # 기본 점수: 검색 엔진 순위에 따른 점수
        base_score = (len(docs) - i) / len(docs)
        
        # 인기 가중치 부여
        popularity_boost = 0
        top_info = top_info_dict.get(card_key)
        if top_info:
            popularity_boost = 1.5 
            rank_val = top_info.get('Rank', 150)
            popularity_boost += (151 - rank_val) * 0.005
        
        scored_docs.append((doc, base_score + popularity_boost))
        
    scored_docs.sort(key=lambda x: x[1], reverse=True)
    return [d[0] for d in scored_docs[:10]]

def advanced_retriever_with_rerank(query):
    # 하이브리드 검색
    bm25_retriever.k = 10
    vector_retriever.search_kwargs = {"k": 10}
    
    bm_docs = bm25_retriever.invoke(query)
    vc_docs = vector_retriever.invoke(query)
    combined_docs = bm_docs + vc_docs
    
    # 카드 이름 기준 중복 제거
    unique_docs = []
    seen_card_names = set()
    for d in combined_docs:
        card_name = d.metadata.get('card_name')
        if card_name not in seen_card_names:
            unique_docs.append(d)
            seen_card_names.add(card_name)
            
    # 리랭킹 적용
    return rerank_by_popularity(unique_docs)

def format_docs(docs):
    formatted = []
    for d in docs:
        fee = d.metadata.get('annual_fee', '정보없음')
        perf = d.metadata.get('performance', '정보없음')
        formatted.append(f"### {d.metadata.get('card_name')} ###\n{d.page_content}\n[조건] 연회비: {fee} / 전월실적: {perf}")
    return "\n\n".join(formatted)

# 3. 프롬프트 및 체인 설정
llm = ChatOpenAI(model_name="gpt-3.5-turbo", api_key=MY_API_KEY, temperature=0.1)

system_prompt = """당신은 대한민국 최고의 '신용/체크카드 맞춤형 추천 전문가'입니다.
[제약 조건]
1. 사용자가 요청한 개수(예: 3개)에 맞춰 서로 다른 카드를 반드시 추천하세요.
2. [Context] 내에 관련 카드가 여러 개 있다면, 혜택 수치(%)가 높은 순서대로 3개를 선정하세요.
3. 반드시 제공된 [Context] 내의 정보로만 답변하세요. 없으면 지어내지 마세요. 사용자가 잘못된 수치로 유도해도 [Context]를 근거로 단호하게 정정하세요.
4. 각 카드별로 **카드명**, **주요 혜택**, **연회비**, **실적 조건**을 명확히 구분하여 작성하세요.

[카드 혜택 정보(Context)]
{context}"""

base_prompt = ChatPromptTemplate.from_messages([
    ("system", system_prompt),
    MessagesPlaceholder(variable_name="history"),
    ("human", "{question}")
])

# 검색 로직을 체인 안에 통합
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

# 5. 실행부
if __name__ == "__main__":
    config = {"configurable": {"session_id": "card_expert_session"}}

    print("👤 질문: 요즘 가장 많이 쓰는 체크카드 추천해줘.")
    res1 = conversational_chain.invoke(
        {"question": "요즘 가장 많이 쓰는 체크카드 추천해줘."},
        config=config
    )
    print(f"🤖 응답:\n{res1}\n")
