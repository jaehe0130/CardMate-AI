# moderation_utils.py
# =========================================================
# [이 파일의 역할]
# - OpenAI Moderation API 호출 전용
# - 유해성 검사 함수(check_moderation)만 분리
# =========================================================

import os
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()


def get_api_key() -> str:
    """
    Streamlit secrets 또는 .env에서 OpenAI API Key를 읽어옵니다.
    """
    try:
        import streamlit as st
        if "OPENAI_API_KEY" in st.secrets:
            return st.secrets["OPENAI_API_KEY"]
    except Exception:
        pass

    return os.getenv("OPENAI_API_KEY", "")


client = OpenAI(api_key=get_api_key())


# =========================================================
# [MODERATION 핵심 함수]
# - 사용자의 입력 질문을 OpenAI Moderation API로 검사
# - flagged=True면 챗봇 답변 생성 전에 차단
# =========================================================
def check_moderation(text: str) -> dict:
    """
    입력 텍스트의 유해성을 검사합니다.

    반환 예시:
    {
        "flagged": False,
        "categories": {...},
        "scores": {...},
        "reason": None
    }
    """
    response = client.moderations.create(input=text)
    result = response.results[0]

    reason = None
    if result.flagged:
        flagged_categories = [
            category
            for category, flagged in result.categories.__dict__.items()
            if flagged
        ]
        reason = ", ".join(flagged_categories) if flagged_categories else "unknown"

    return {
        "flagged": result.flagged,
        "categories": result.categories.__dict__,
        "scores": result.category_scores.__dict__,
        "reason": reason,
    }
