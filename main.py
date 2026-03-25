import os
import json
import tempfile
from typing import List, Dict

import streamlit as st
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_chroma import Chroma
from langchain.schema import Document


st.set_page_config(
    page_title="CardMate AI",
    page_icon="💳",
    layout="wide"
)

st.markdown("""
<style>
.block-container {
    padding-top: 2rem;
    padding-bottom: 2rem;
    max-width: 1100px;
}
.recommend-card {
    background: white;
    border: 1px solid #e5e7eb;
    border-radius: 18px;
    padding: 20px;
    margin-bottom: 16px;
    box-shadow: 0 6px 18px rgba(0,0,0,0.05);
}
.rank-badge {
    display: inline-block;
    padding: 6px 10px;
    border-radius: 999px;
    background: #eff6ff;
    color: #1d4ed8;
    font-size: 0.82rem;
    font-weight: 700;
    margin-bottom: 10px;
}
.meta-text {
    color: #6b7280;
    font-size: 0.92rem;
}
</style>
""", unsafe_allow_html=True)


def get_api_key():
    if "OPENAI_API_KEY" in st.secrets:
        return st.secrets["OPENAI_API_KEY"]
    return os.getenv("OPENAI_API_KEY")


API_KEY = get_api_key()
if not API_KEY:
    st.error("OPENAI_API_KEY가 설정되지 않았습니다.")
    st.stop()


@st.cache_data
def load_card_data(path: str) -> List[Dict]:
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    if isinstance(data, dict):
        if "cards" in data:
            data = data["cards"]
        else:
            data = [data]
    return data


def safe_str(x):
    if x is None:
        return ""
    return str(x)


def card_to_text(card: Dict) -> str:
    """
    지금 top_card_data.json 구조에 맞는 검색용 텍스트
    """
    rank = safe_str(card.get("Rank"))
    name = safe_str(card.get("Card_Name"))
    company = safe_str(card.get("Card_Company"))
    card_type = safe_str(card.get("Card_Type"))
    rank_category = safe_str(card.get("Rank_Category"))

    # 카드명 자체에 여행/쇼핑/마일리지/트래블/오일 같은 힌트가 들어있는 경우가 많아서
    # 이름과 카테고리를 최대한 검색 텍스트에 녹여줌
    text = f"""
카드명: {name}
카드사: {company}
카드종류: {card_type}
랭킹: {rank}위
랭킹카테고리: {rank_category}
이 카드는 {rank_category} 랭킹에 포함된 {card_type}이며 카드사는 {company}이고 카드명은 {name}이다.
""".strip()
    return text


@st.cache_resource
def build_vectorstore(cards: List[Dict]):
    embeddings = OpenAIEmbeddings(
        api_key=API_KEY,
        model="text-embedding-3-small"
    )

    docs = []
    for i, card in enumerate(cards):
        docs.append(
            Document(
                page_content=card_to_text(card),
                metadata={
                    "idx": i,
                    "Card_Name": safe_str(card.get("Card_Name")),
                    "Card_Company": safe_str(card.get("Card_Company")),
                    "Card_Type": safe_str(card.get("Card_Type")),
                    "Rank": safe_str(card.get("Rank")),
                    "Rank_Category": safe_str(card.get("Rank_Category")),
                }
            )
        )

    persist_dir = os.path.join(tempfile.gettempdir(), "cardmate_rank_db")

    vectorstore = Chroma.from_documents(
        documents=docs,
        embedding=embeddings,
        persist_directory=persist_dir,
        collection_name="top_card_data_collection"
    )
    return vectorstore


def retrieve_cards(vectorstore, query: str, top_k: int = 10):
    retriever = vectorstore.as_retriever(search_kwargs={"k": top_k})
    return retriever.invoke(query)


def rerank_cards(query: str, retrieved_docs: List[Document], cards: List[Dict]) -> List[Dict]:
    llm = ChatOpenAI(
        model="gpt-4o-mini",
        api_key=API_KEY,
        temperature=0
    )

    candidates = []
    for i, doc in enumerate(retrieved_docs, start=1):
        idx = doc.metadata["idx"]
        card = cards[idx]

        candidates.append(f"""
[후보 {i}]
candidate_number: {i}
카드명: {safe_str(card.get("Card_Name"))}
카드사: {safe_str(card.get("Card_Company"))}
카드종류: {safe_str(card.get("Card_Type"))}
랭킹: {safe_str(card.get("Rank"))}
랭킹카테고리: {safe_str(card.get("Rank_Category"))}
""".strip())

    prompt = f"""
당신은 카드 추천 도우미입니다.

사용자 질문:
{query}

아래는 검색으로 찾은 카드 후보들입니다.
이 중 사용자 질문에 가장 맞는 카드 3개를 다시 고르세요.

판단 기준:
1. 사용자 질문과 카드명 의미의 관련성
2. 카드종류(신용카드/체크카드) 일치 여부
3. 랭킹이 높을수록 약간 가산점
4. 카드명에 포함된 키워드(Travel, Oil, Shopping, Mileage, Digital, Air 등)를 적극 활용

중요:
- 제공된 후보 안에서만 고르세요.
- JSON만 출력하세요.
- 정확히 3개만 고르세요.

출력 형식:
{{
  "top3": [
    {{
      "candidate_number": 1,
      "score": 95,
      "reason": "사용자 질문과 가장 관련성이 높음"
    }},
    {{
      "candidate_number": 2,
      "score": 91,
      "reason": "..."
    }},
    {{
      "candidate_number": 3,
      "score": 88,
      "reason": "..."
    }}
  ]
}}

후보 목록:
{chr(10).join(candidates)}
""".strip()

    try:
        result = llm.invoke(prompt)
        content = result.content.strip()
        content = content.replace("```json", "").replace("```", "").strip()
        parsed = json.loads(content)

        final_cards = []
        for item in parsed["top3"]:
            cnum = item["candidate_number"]
            score = item["score"]
            reason = item["reason"]

            doc = retrieved_docs[cnum - 1]
            idx = doc.metadata["idx"]
            card = cards[idx].copy()
            card["_rerank_score"] = score
            card["_rerank_reason"] = reason
            final_cards.append(card)

        return final_cards

    except Exception:
        fallback = []
        for doc in retrieved_docs[:3]:
            idx = doc.metadata["idx"]
            card = cards[idx].copy()
            card["_rerank_score"] = 0
            card["_rerank_reason"] = "rerank 실패로 1차 검색 결과를 사용했습니다."
            fallback.append(card)
        return fallback


def generate_answer(query: str, top_cards: List[Dict]) -> str:
    llm = ChatOpenAI(
        model="gpt-4o-mini",
        api_key=API_KEY,
        temperature=0.3
    )

    cards_text = []
    for i, card in enumerate(top_cards, start=1):
        cards_text.append(f"""
[{i}위 카드]
카드명: {safe_str(card.get("Card_Name"))}
카드사: {safe_str(card.get("Card_Company"))}
카드종류: {safe_str(card.get("Card_Type"))}
랭킹: {safe_str(card.get("Rank"))}
랭킹카테고리: {safe_str(card.get("Rank_Category"))}
추천이유: {safe_str(card.get("_rerank_reason"))}
""".strip())

    prompt = f"""
당신은 카드 추천 상담사입니다.

사용자 질문:
{query}

선정된 카드:
{chr(10).join(cards_text)}

중요:
- 현재 데이터에는 카드명, 카드사, 카드종류, 랭킹 정보만 있습니다.
- 실제 혜택, 연회비, 전월실적 정보는 현재 없습니다.
- 따라서 혜택을 단정해서 말하면 안 됩니다.
- 카드명과 카드 유형, 랭킹 정보를 바탕으로 왜 후보로 골랐는지 설명하세요.
- 마지막에 "정확한 혜택은 상세 상품설명 확인이 필요하다"는 취지의 안내를 포함하세요.
- 마크다운으로 자연스럽게 작성하세요.
""".strip()

    return llm.invoke(prompt).content


st.title("💳 CardMate AI")
st.caption("top_card_data.json 기반 랭킹형 카드 추천")

if "messages" not in st.session_state:
    st.session_state.messages = []

json_path = "top_card_data.json"
if not os.path.exists(json_path):
    st.error("top_card_data.json 파일이 없습니다.")
    st.stop()

cards = load_card_data(json_path)
vectorstore = build_vectorstore(cards)

with st.sidebar:
    st.subheader("질문 예시")
    st.markdown("""
- 여행용 체크카드 추천해줘
- 마일리지 적립 느낌의 카드 추천
- 쇼핑에 어울릴 것 같은 카드 추천
- 대학생이 쓸 만한 체크카드 추천
- 교통/일상용으로 무난한 카드 추천
- 해외 관련 느낌의 카드 추천
    """)
    st.divider()
    st.write(f"카드 수: {len(cards)}개")

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

query = st.chat_input("예: 여행용 체크카드 추천해줘")

if query:
    st.session_state.messages.append({"role": "user", "content": query})

    with st.chat_message("user"):
        st.markdown(query)

    with st.chat_message("assistant"):
        with st.spinner("카드를 찾고 있어요..."):
            retrieved = retrieve_cards(vectorstore, query, top_k=10)
            top_cards = rerank_cards(query, retrieved, cards)
            answer = generate_answer(query, top_cards)

            st.markdown(answer)
            st.markdown("### 추천 카드 3개")

            for i, card in enumerate(top_cards, start=1):
                st.markdown('<div class="recommend-card">', unsafe_allow_html=True)
                st.markdown(f'<div class="rank-badge">{i}위 추천</div>', unsafe_allow_html=True)
                st.markdown(f"### {safe_str(card.get('Card_Name'))}")
                st.markdown(f"**카드사**: {safe_str(card.get('Card_Company'))}")
                st.markdown(f"**카드종류**: {safe_str(card.get('Card_Type'))}")
                st.markdown(f"**전체 랭킹**: {safe_str(card.get('Rank'))}")
                st.markdown(f"**랭킹 카테고리**: {safe_str(card.get('Rank_Category'))}")
                st.markdown(f"**선정 이유**: {safe_str(card.get('_rerank_reason'))}")
                st.markdown('</div>', unsafe_allow_html=True)

            st.session_state.messages.append({"role": "assistant", "content": answer})
