import os
import shutil
import zipfile
import streamlit as st
import gdown

DB_DIR = "./card_semantic_db_v2"
ZIP_PATH = "./card_semantic_db_v2.zip"

def ensure_vector_db():
    if os.path.exists(DB_DIR) and os.path.isdir(DB_DIR) and len(os.listdir(DB_DIR)) > 0:
        return

    if os.path.exists(DB_DIR):
        shutil.rmtree(DB_DIR, ignore_errors=True)

    if os.path.exists(ZIP_PATH):
        os.remove(ZIP_PATH)

    gdrive_url = st.secrets["GDRIVE_DB_URL"]

    with st.spinner("추천 DB를 다운로드하고 있습니다. 처음 1회만 시간이 걸릴 수 있어요..."):
        gdown.download(
            url=gdrive_url,
            output=ZIP_PATH,
            quiet=False,
            fuzzy=True
        )

        if not os.path.exists(ZIP_PATH):
            raise FileNotFoundError("Google Drive에서 DB zip 다운로드에 실패했습니다.")

        with zipfile.ZipFile(ZIP_PATH, "r") as zip_ref:
            zip_ref.extractall(".")

        if not os.path.exists(DB_DIR):
            raise FileNotFoundError(
                "압축 해제 후 card_semantic_db_v2 폴더를 찾지 못했습니다. "
                "zip 내부 최상위 폴더명이 card_semantic_db_v2인지 확인하세요."
            )

        os.remove(ZIP_PATH)
