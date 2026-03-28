# recommender.py
from openai import OpenAI
from langchain_core.documents import Document


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
        "flagged": result.flagged,
        "categories": result.categories.__dict__,
        "scores": result.category_scores.__dict__,  # 각 항목의 위험도 점수
        "reason": reason,
    }


# =========================
# 2. RRF
# =========================
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


# =========================
# 3. 인기순 리랭킹
# =========================
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
    return [d[0] for d in scored_docs[:10]]10]]



# =========================
# 4. 검색 + 병합 + 리랭크
# =========================
def advanced_retriever_with_rerank(query):
    # 🌟 1. 질문 의도 파악 (10대 여부 확인)
    is_teenager = any(
        keyword in query
        for keyword in ["10대", "청소년", "학생", "중학생", "고등학생", "미성년자"]
    )

    # 🌟 2. 검색기 세팅 (필터 적용)
    if is_teenager:
        vector_retriever.search_kwargs = {"k": 10, "filter": {"card_type": "체크카드"}}
    else:
        vector_retriever.search_kwargs = {"k": 10}
    bm25_retriever.k = 10

    # 🌟 3. 실제 검색 실행 (하이브리드 검색)
    bm_docs = bm25_retriever.invoke(query)
    vc_docs = vector_retriever.invoke(query)
    combined_docs = bm_docs + vc_docs

    # 🌟 4. 인기 카드 강제 주입 로직 (이름 공백 제거 매칭 적용)
    if any(
        keyword in query
        for keyword in ["인기", "많이 쓰는", "순위", "1위", "대세", "추천"]
    ):
        if is_teenager:
            candidate_cards = [
                c for c in all_cards_from_db.values() if c["Card_Type"] == "체크카드"
            ]
        else:
            candidate_cards = list(all_cards_from_db.values())

        top_5_cards = sorted(candidate_cards, key=lambda x: x["Rank"])[:5]
        top_5_names = [c["Card_Name"] for c in top_5_cards]

        # 띄어쓰기가 달라도 매칭되도록 공백 제거 후 비교
        def clean(t):
            return str(t).replace(" ", "").strip()

        clean_top_5 = [clean(n) for n in top_5_names]

        for doc in documents:
            if clean(doc.metadata.get("card_name", "")) in clean_top_5:
                combined_docs.append(doc)

# =========================
# 5. LLM에 넣을 Context 문자열 변환
# =========================
def format_docs(docs):
    formatted = []
    # enumerate를 사용해 리랭킹된 순서(idx)를 가져옵니다.
    for idx, d in enumerate(docs):
        fee = d.metadata.get("annual_fee", "정보없음")
        perf = d.metadata.get("performance", "정보없음")

        # 🌟 핵심: LLM이 딴짓을 못하도록 헤더에 [추천 N순위]를 강제로 박아버립니다.
        doc_text = f"[[🔥 추천 {idx+1}순위 문서 🔥]]\n### {d.metadata.get('card_name')} ###\n{d.page_content}\n[조건] 연회비: {fee} / 전월실적: {perf}"
        formatted.append(doc_text)

    return "\n\n".join(formatted)


# =========================
# 6. context 생성 helper
# =========================
def build_context(
    question: str,
    bm25_retriever,
    vector_retriever,
    documents: list,
    all_cards_from_db: dict,
) -> str:
    """
    질문 -> 검색/리랭크 -> context 문자열 생성
    """
    docs = advanced_retriever_with_rerank(
        query=question,
        bm25_retriever=bm25_retriever,
        vector_retriever=vector_retriever,
        documents=documents,
        all_cards_from_db=all_cards_from_db,
    )
    return format_docs(docs)
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

# =========================
# 7. chat 실행 helper
# =========================
def run_card_recommendation_chat(
    question: str,
    client: OpenAI,
    conversational_chain,
    config: dict,
    bm25_retriever,
    vector_retriever,
    documents: list,
    all_cards_from_db: dict,
) -> str:
    """
    moderation 검사 후 conversational_chain 실행
    prompt는 app.py에서 정의했다고 가정
    """
    moderation_result = check_moderation(client, question)
    if moderation_result["flagged"]:
        return "부적절한 내용이 포함되어 있어 답변할 수 없습니다."

    docs = advanced_retriever_with_rerank(
        query=question,
        bm25_retriever=bm25_retriever,
        vector_retriever=vector_retriever,
        documents=documents,
        all_cards_from_db=all_cards_from_db,
    )

    if not docs:
        return "조건에 맞는 카드 정보를 찾지 못했습니다. 혜택 키워드를 조금 더 구체적으로 입력해 주세요."

    return conversational_chain.invoke({"question": question}, config=config)
