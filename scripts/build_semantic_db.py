import os
import json
import shutil
from dotenv import load_dotenv
from langchain_core.documents import Document
from langchain_community.vectorstores import Chroma
from langchain_openai import OpenAIEmbeddings

# 1. 환경 설정 및 API 키 로드
load_dotenv()
MY_API_KEY = os.getenv('OPENAI_API_KEY')

# ====================================================================
# [Step 1] 기존 Vector DB 폴더 깔끔하게 삭제하기 (초기화)
# ====================================================================
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")

PERSIST_DIR = os.path.join(DATA_DIR, "card_semantic_db")
CARD_DATA_PATH = os.path.join(DATA_DIR, "card_data.json")

if os.path.exists(PERSIST_DIR):
    print(f"🧹 기존 DB 폴더('{PERSIST_DIR}')를 발견했습니다. 깨끗하게 삭제하고 초기화합니다...")
    shutil.rmtree(PERSIST_DIR)
else:
    print(f"✨ 새로운 DB 폴더('{PERSIST_DIR}')를 생성할 준비가 되었습니다.")

# ====================================================================
# [Step 2] 마스터 데이터 로드 및 시맨틱 청킹 (1 혜택 = 1 청크)
# ====================================================================
print("📂 'card_data.json' 데이터를 불러와 시맨틱 청킹을 시작합니다...")

with open(CARD_DATA_PATH, 'r', encoding='utf-8') as f:
    card_data = json.load(f)

semantic_docs = []

for card in card_data:
    # 메타데이터용 핵심 정보 추출
    card_name = card.get("Card_Name", "이름 없음")
    card_type = card.get("Card_Type", "구분 없음")
    company = card.get("Card_Company", "카드사 없음")
    perf = card.get("Base_Perf_Num", 0)
    fee_dom = card.get("Annual_Fee_Domestic", 0)
    fee_ovs = card.get("Annual_Fee_Overseas", 0)
    image_url = card.get("Image_URL", "")
    
    # 정제된 혜택 요약 리스트
    benefits = card.get("Benefits_Summary", [])
    
    # 혜택 정보가 전혀 없는 깡통 카드 방어 로직
    if not benefits:
        chunk_text = f"카드명: {card_name}\n분류: {card_type}\n연회비: 국내 {fee_dom}원, 해외 {fee_ovs}원\n이 카드는 특별한 상세 혜택 요약 정보가 없습니다."
        metadata = {
            "card_name": card_name,
            "card_company": company,
            "card_type": card_type,
            "performance": perf,
            "annual_fee": fee_dom,
            "image_url": image_url
        }
        semantic_docs.append(Document(page_content=chunk_text, metadata=metadata))
        continue

    # 시맨틱 청킹: 혜택 1개를 1개의 청크(Document)로 분리
    for b in benefits:
        chunk_text = f"카드명: {card_name}\n분류: {card_type}\n혜택 내용: {b}"
        
        metadata = {
            "card_name": card_name,
            "card_company": company,
            "card_type": card_type,
            "performance": perf,
            "annual_fee": fee_dom,
            "image_url": image_url
        }
        
        semantic_docs.append(Document(page_content=chunk_text, metadata=metadata))

print(f"✂️ 청킹 완료! {len(card_data)}개의 카드가 {len(semantic_docs)}개의 정교한 의미 조각으로 쪼개졌습니다.")

# ====================================================================
# [Step 3] OpenAI 임베딩 및 Chroma DB에 저장
# ====================================================================
print(f"🚀 OpenAI 임베딩을 시작합니다. (조각 개수: {len(semantic_docs)}개) API 통신 중...")

embeddings = OpenAIEmbeddings(
    api_key=MY_API_KEY,
    model="text-embedding-3-small"
)

semantic_vector_db = Chroma.from_documents(
    documents=semantic_docs,
    embedding=embeddings,
    persist_directory=PERSIST_DIR
)

print(f"🎉 성공! 고도화(Advanced) 모델용 시맨틱 DB가 '{PERSIST_DIR}' 폴더에 완벽하게 저장되었습니다!")
