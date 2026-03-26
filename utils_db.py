# utils_db.py
# =========================================================
# [이 파일의 역할]
# - Google Drive에 올린 Chroma DB zip 다운로드
# - 압축 해제 후 ./card_semantic_db_v3 폴더 준비
# =========================================================

import os
import shutil
import zipfile
import streamlit as st
import gdown

DB_DIR = "./card_semantic_db_v3"
ZIP_PATH = "./card_semantic_db_v3.zip"


def ensure_vector_db():
    """
    DB 폴더가 없으면 Google Drive에서 zip 다운로드 후 압축 해제.
    """
    if os.path.exists(DB_DIR) and os.path.isdir(DB_DIR) and len(os.listdir(DB_DIR)) > 0:
        return

    if os.path.exists(DB_DIR):
        shutil.rmtree(DB_DIR, ignore_errors=True)

    if os.path.exists(ZIP_PATH):
        os.remove(ZIP_PATH)

    gdrive_url = st.secrets["GDRIVE_DB_URL"]

    with st.spinner("추천 DB를 다운로드하고 있습니다..."):
        gdown.download(
            url=gdrive_url,
            output=ZIP_PATH,
            quiet=False,
            fuzzy=True
        )

        if not os.path.exists(ZIP_PATH):
            raise FileNotFoundError("Google Drive에서 DB zip 다운로드 실패")

        with zipfile.ZipFile(ZIP_PATH, "r") as zip_ref:
            zip_ref.extractall(".")

        if not os.path.exists(DB_DIR):
            raise FileNotFoundError("압축 해제 후 card_semantic_db_v3 폴더를 찾지 못했습니다.")

        os.remove(ZIP_PATH)
