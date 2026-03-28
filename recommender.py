# recommender.py
from openai import OpenAI
from langchain_openai import ChatOpenAI
from langchain_core.documents import Document

# utils_db.py
import os
import shutil
import zipfile
from pathlib import Path

import gdown
import streamlit as st
from langchain_core.documents import Document
from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import Chroma
from langchain_community.retrievers import BM25Retriever


DB_ZIP_PATH = Path("./card_semantic_db_v3.zip")
DB_EXTRACT_ROOT = Path("./db_cache")
DB_DIR = DB_EXTRACT_ROOT / "card_semantic_db_v3"


def download_and_prepare_db(file_id: str) -> str:
    """
    구글드라이브에서 card_semantic_db_v3.zip 다운로드 후 압축 해제.
    반환값: 실제 Chroma persist_directory 경로
    """
    DB_EXTRACT_ROOT.mkdir(parents=True, exist_ok=True)

    # 이미 압축 해제된 폴더가 있으면 재사용
    if DB_DIR.exists() and any(DB_DIR.iterdir()):
        return str(DB_DIR)

    # 기존 zip 제거
    if DB_ZIP_PATH.exists():
        DB_ZIP_PATH.unlink()

    url = f"https://drive.google.com/uc?id={file_id}"
    gdown.download(url, str(DB_ZIP_PATH), quiet=False)

    if not DB_ZIP_PATH.exists():
        raise FileNotFoundError("DB zip 다운로드 실패")

    # 기존 압축 폴더 초기화
    if DB_EXTRACT_ROOT.exists():
        shutil.rmtree(DB_EXTRACT_ROOT)
    DB_EXTRACT_ROOT.mkdir(parents=True, exist_ok=True)

    # 압축 해제
    with zipfile.ZipFile(DB_ZIP_PATH, "r") as zip_ref:
        zip_ref.extractall(DB_EXTRACT_ROOT)

    # 1) 정상 구조: db_cache/card_semantic_db_v3/
    if DB_DIR.exists() and any(DB_DIR.iterdir()):
        return str(DB_DIR)

    extracted_items = list(DB_EXTRACT_ROOT.iterdir())

    # 2) zip 내부에 파일들이 바로 있는 경우
    if extracted_items and any(item.is_file() for item in extracted_items):
        DB_DIR.mkdir(parents=True, exist_ok=True)
        for item in extracted_items:
            if item.name != "card_semantic_db_v3":
                shutil.move(str(item), str(DB_DIR / item.name))
        return str(DB_DIR)

    # 3) zip 내부에 폴더 하나만 있고 그게 실제 DB 폴더인 경우
    if len(extracted_items) == 1 and extracted_items[0].is_dir():
        return str(extracted_items[0])

    raise FileNotFoundError("압축 해제 후 Chroma DB 폴더를 찾지 못했습니다.")


@st.cache_resource(show_spinner=True)
def load_rag_resources(openai_api_key: str, gdrive_db_file_id: str):
    """
    구글드라이브 zip → 압축 해제 → Chroma 로드 → BM25/Vector Retriever 생성
    """
    db_path = download_and_prepare_db(gdrive_db_file_id)

    embeddings = OpenAIEmbeddings(
        api_key=openai_api_key,
        model="text-embedding-3-small"
    )

    vector_db = Chroma(
        persist_directory=db_path,
        embedding_function=embeddings
    )

    all_data = vector_db.get()
    documents_raw = all_data.get("documents", [])
    metadatas_raw = all_data.get("metadatas", [])

    if not documents_raw or not metadatas_raw:
        raise ValueError("벡터 DB가 비어 있습니다. zip 내용 확인 필요")

    documents = [
        Document(page_content=doc, metadata=meta)
        for doc, meta in zip(documents_raw, metadatas_raw)
    ]

    if not documents:
        raise ValueError("문서 복구 결과가 비어 있습니다.")

    bm25_retriever = BM25Retriever.from_documents(documents)
    bm25_retriever.k = 10

    vector_retriever = vector_db.as_retriever(search_kwargs={"k": 10})

    all_cards_from_db = {}
    for doc in documents:
        meta = doc.metadata or {}
    
        name = meta.get("card_name")
        rank = meta.get("rank", 999)
        card_type = meta.get("card_type", "")
        image_url = meta.get("Image_URL", "") or meta.get("image_url", "")
    
        try:
            rank = int(rank)
        except:
            rank = 999
    
        if name and name not in all_cards_from_db:
            all_cards_from_db[name] = {
                "Card_Name": name,
                "Rank": rank,
                "Card_Type": card_type,
                "Image_URL": image_url
            }

    return {
        "db_path": db_path,
        "vector_db": vector_db,
        "documents": documents,
        "bm25_retriever": bm25_retriever,
        "vector_retriever": vector_retriever,
        "all_cards_from_db": all_cards_from_db,
    }

# ──────────────────────────────────────────────
# Moderation 함수
# ──────────────────────────────────────────────
def check_moderation(text: str) -> dict:
    """
    OpenAI Moderation API로 입력 텍스트의 유해성을 검사합니다.

    반환값:
    {
        "flagged"    : True/False,
        "categories" : {            
            "hate"        : False,
            "harassment"  : False,
            "self-harm"   : False,
            "sexual"      : False,
            "violence"    : False,
            ...
        },
        "reason" : "hate"                ← flagged된 경우 이유 (없으면 None)
    }

    사용 예시:
        result = check_moderation("좋은 카드 추천해줘")
        result["flagged"]  # → False (정상)

        result = check_moderation("폭력적인 내용")
        result["flagged"]  # → True (차단)
        result["reason"]   # → "violence"
    """
    response = client.moderations.create(input=text)
    result = response.results[0]

    # flagged된 카테고리 찾기
    reason = None
    if result.flagged:
        # categories 딕셔너리에서 True인 항목만 추출
        flagged_categories = [
            category
            for category, flagged in result.categories.__dict__.items()
            if flagged
        ]
        reason = ", ".join(flagged_categories) if flagged_categories else "unknown"

    return {
        "flagged"    : result.flagged,
        "categories" : result.categories.__dict__,
        "scores"     : result.category_scores.__dict__,  # 각 항목의 위험도 점수
        "reason"     : reason
    }


def reciprocal_rank_fusion(results_list: list, k: int = 60) -> list:
    """
    RAG-Fusion: BM25 + 벡터 검색 결과를 RRF 알고리즘으로 합산
    두 검색 모두에서 상위권인 카드일수록 높은 점수
    k=60은 RRF 표준 상수값 (RRF 논문 참조)
    """
    scores = {}
    doc_map = {}

    for results in results_list:
        for rank, doc in enumerate(results):
            key = doc.page_content[:50]
            if key not in scores:
                scores[key] = 0
                doc_map[key] = doc
            scores[key] += 1 / (rank + k)

    sorted_keys = sorted(scores, key=lambda x: scores[x], reverse=True)
    return [doc_map[key] for key in sorted_keys]


# 2. 검색 고도화 로직 (하이브리드 + 리랭킹)
def rerank_by_popularity(docs):
    scored_docs = []
    for i, doc in enumerate(docs):
        base_score = (len(docs) - i) / len(docs)
        
        # 메타데이터에서 바로 순위(Rank)를 꺼내옴 (딕셔너리 대조 필요 없음!)
        rank_val = doc.metadata.get('rank', 999)
        
        # 150위 안쪽인 카드만 가중치 팍팍 부여
        if rank_val <= 150:
            popularity_boost = 5.0 + (151 - rank_val) * 0.1
        else:
            popularity_boost = 0.0
            
        scored_docs.append((doc, base_score + popularity_boost))
        
    scored_docs.sort(key=lambda x: x[1], reverse=True)
    return [d[0] for d in scored_docs[:10]]


def advanced_retriever_with_rerank(query):
    # 🌟 1. 질문 의도 파악 (10대 여부 확인)
    is_teenager = any(keyword in query for keyword in ["10대", "청소년", "학생", "중학생", "고등학생", "미성년자"])

    # 🌟 2. 검색기 세팅 (필터 적용)
    if is_teenager:
        vector_retriever.search_kwargs = {"k": 10, "filter": {"card_type": "체크카드"}}
    else:
        vector_retriever.search_kwargs = {"k": 10}
    bm25_retriever.k = 10

    # 🌟 3. 실제 검색 실행 (하이브리드 검색)
    bm_docs = bm25_retriever.invoke(query)
    vc_docs = vector_retriever.invoke(query)
    # combined_docs = bm_docs + vc_docs
    combined_docs = reciprocal_rank_fusion([bm_docs, vc_docs]) # RAG-fuwion

    # 🌟 4. 인기 카드 강제 주입 로직 (이름 공백 제거 매칭 적용)
    if any(keyword in query for keyword in ["인기", "많이 쓰는", "순위", "1위", "대세", "추천"]):
        if is_teenager:
            candidate_cards = [c for c in all_cards_from_db.values() if c['Card_Type'] == '체크카드']
        else:
            candidate_cards = list(all_cards_from_db.values())
            
        top_5_cards = sorted(candidate_cards, key=lambda x: x['Rank'])[:5]
        top_5_names = [c['Card_Name'] for c in top_5_cards]
        
        # 띄어쓰기가 달라도 매칭되도록 공백 제거 후 비교
        def clean(t): return str(t).replace(" ", "").strip()
        clean_top_5 = [clean(n) for n in top_5_names]

        for doc in documents: 
            if clean(doc.metadata.get('card_name', '')) in clean_top_5:
                combined_docs.append(doc)

    # ====================================================================
    # 🌟 5. [핵심 수술 부위] 혜택 병합(Merge) 로직 (기존 seen_card_names 대체!)
    # ====================================================================
    card_grouped_docs = {}
    
    for d in combined_docs:
        card_name = d.metadata.get('card_name')
        card_type = str(d.metadata.get('card_type', ''))
        
        # 결측치 방어 및 10대 신용카드 사후 컷팅
        if not card_name or str(card_name).strip() == "" or str(card_name).lower() == "nan":
            continue
        if is_teenager and "신용" in card_type:
            continue
            
        # 1. 딕셔너리에 카드가 처음 등장하면? -> 새 방을 만들고 첫 번째 혜택을 넣습니다.
        if card_name not in card_grouped_docs:
            card_grouped_docs[card_name] = {"metadata": d.metadata, "benefits": [d.page_content]}
        
        # 2. 이미 방이 있는 카드라면? -> 기존 혜택들 밑에 새로운 혜택(d.page_content)을 추가(Append)합니다!
        else:
            # 단, 내용이 완전히 똑같은 조각(BM25와 Vector가 중복으로 가져온 녀석)만 거릅니다.
            if d.page_content not in card_grouped_docs[card_name]["benefits"]:
                card_grouped_docs[card_name]["benefits"].append(d.page_content)
                
    # 3. 차곡차곡 모은 혜택들을 엔터(\n)로 이어붙여서 하나의 완성된 Document로 만듭니다.
    unique_docs = []
    for c_name, data in card_grouped_docs.items():
        # GPT-3.5 모델 용량 초과를 막기 위해 카드 한 장당 최대 2000자로 제한
        combined_text = "\n".join(data["benefits"])[:2000]
        unique_docs.append(Document(page_content=combined_text, metadata=data["metadata"]))
    # ====================================================================

    # 🌟 6. 리랭킹 적용 후 상위 3개만 LLM에게 전달 (최적화)
    return rerank_by_popularity(unique_docs)[:3]


def format_docs(docs):
    formatted = []
    # enumerate를 사용해 리랭킹된 순서(idx)를 가져옵니다.
    for idx, d in enumerate(docs): 
        fee = d.metadata.get('annual_fee', '정보없음')
        perf = d.metadata.get('performance', '정보없음')
        
        # 🌟 핵심: LLM이 딴짓을 못하도록 헤더에 [추천 N순위]를 강제로 박아버립니다.
        doc_text = f"[[🔥 추천 {idx+1}순위 문서 🔥]]\n### {d.metadata.get('card_name')} ###\n{d.page_content}\n[조건] 연회비: {fee} / 전월실적: {perf}"
        formatted.append(doc_text)
        
    return "\n\n".join(formatted)

# 3. 프롬프트 및 체인 설정
llm = ChatOpenAI(model_name="gpt-3.5-turbo", api_key=MY_API_KEY, temperature=0.1)

system_prompt = """당신은 대한민국 최고의 '신용/체크카드 맞춤형 추천 전문가(Financial Advisor)'입니다.
반드시 제공된 [카드 혜택 정보(Context)]만을 바탕으로 사용자의 질문에 가장 적합한 카드를 추천하세요.

[제약 조건 (Strict Rules)]
1. 정보의 절대성 (No Hallucination): [Context]에 명시되지 않은 혜택, 연회비, 실적 조건은 절대 지어내지 마세요. 제공된 정보에 없다면 "제공된 정보에서는 확인할 수 없습니다"라고 명확히 답변하세요.
2. 사용자 니즈 정밀 매칭: 사용자의 질문(예: 주유, 마트, 무실적 등)과 가장 관련성이 높은 혜택을 가진 카드를 우선 추천하고, 해당 혜택의 '구체적인 수치(%, 원)'를 반드시 포함하세요.
3. 가스라이팅 방어 (Anti-Sycophancy): 사용자가 [Context]와 다른 잘못된 수치나 정보로 유도하더라도 절대 동조하지 마세요. [Context]의 팩트를 기반으로 정중하고 단호하게 정정하세요.
4. 조건 교차 검증: 혜택 본문 내용에 적힌 실적 조건(예: '전월 30만원 이상 시 제공')이 하단의 '[조건]' 메타데이터보다 우선합니다.
5. 다중 선택지 제공 (Provide Options): 사용자가 특정 개수를 지정하지 않더라도, 사용자가 비교하고 선택할 수 있도록 [Context] 내에서 가장 적합한 카드 **3개**를 반드시 찾아 추천하세요.
6. 카드 종류 준수 (Card Type Compliance):
   - 사용자가 '체크카드'를 요청한 경우, 반드시 체크카드만 추천하세요. 신용카드는 절대 포함하지 마세요.
   - 사용자가 '신용카드'를 요청한 경우, 반드시 신용카드만 추천하세요. 체크카드는 절대 포함하지 마세요.
   - 사용자가 카드 종류를 특정하지 않은 경우, 신용카드와 체크카드 모두 추천 가능합니다.
7. 단계적 사고 (Chain-of-Thought): 카드를 추천하기 전에 반드시 아래 3단계 분석을 먼저 수행하세요.
   - [1단계: 소비 패턴 분석] 사용자의 질문에서 주요 지출 카테고리와 필요 혜택을 파악하세요.
   - [2단계: 카드 적합성 검토] [Context]의 각 카드가 사용자 니즈와 얼마나 부합하는지 비교하세요.
   - [3단계: 최적 카드 선정] 분석 결과를 바탕으로 가장 적합한 카드를 순서대로 선정하세요.

[출력 형식 (Output Format)]
추천하는 카드가 여러 개일 경우 아래 형식을 반복해서 사용하고, 가독성을 높이기 위해 마크다운을 엄격히 적용하세요.
아래 형식을 반드시 순서대로 따르세요.

**[소비 패턴 분석]**
(사용자의 주요 지출 카테고리와 필요 혜택을 1~2줄로 요약)

**[추천 카드]**
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
    MessagesPlaceholder(variable_name="history"),
    ("human", "{question}")
])

# 🌟 중요: 검색 로직을 체인 안에 통합
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

# Moderation
def chat(question: str, config: dict) -> str:
    # Moderation 검사
    moderation_result = check_moderation(question)
    if moderation_result["flagged"]:
        reason = moderation_result["reason"]
        print(f"[Moderation 차단] 사유: {reason}")
        return f"부적절한 내용이 포함되어 있어 답변할 수 없습니다."

    # 정상이면 체인 실행
    return conversational_chain.invoke({"question": question}, config=config)

