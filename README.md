
diff --git a/README.md b/README.md
index 12f819f4bd3a25a268bafdfab00360dbdebaff77..98cf9434e8d5a1ddcd95b325dfbd5a574f75fd1a 100644
--- a/README.md
+++ b/README.md
@@ -1 +1,63 @@
-# CardMate-AI
\ No newline at end of file
+# CardMate-AI
+
+Streamlit 기반 카드 추천 앱입니다. 사용자가 입력한 조건(예: 편의점, 교통, 배달, 해외여행)에 맞춰 카드 혜택을 검색하고, LLM 답변 + 카드 비교 UI를 제공합니다.
+
+## 프로젝트 구조
+
+```text
+CardMate-AI/
+├── main.py                 # Streamlit 엔트리포인트(UI)
+├── prompts.py              # LLM 프롬프트/체인 구성 + moderation 후 실행
+├── recommender.py          # 하이브리드 검색(BM25 + Vector) + 카드 리랭킹
+├── utils_db.py             # Google Drive에서 Chroma DB 다운로드/압축해제
+├── moderation_utils.py     # OpenAI Moderation API 호출
+├── requirements.txt        # 의존성
+├── .env.example            # 로컬 환경변수 예시
+└── .streamlit/
+    ├── config.toml         # Streamlit 기본 설정
+    └── secrets.toml.example# Streamlit secrets 예시
+```
+
+## 1) 설치
+
+```bash
+pip install -r requirements.txt
+```
+
+## 2) 환경 변수/시크릿 설정
+
+### 방법 A: `.env` 사용(로컬 개발)
+
+`.env.example`를 복사해 `.env`를 만든 뒤 값을 채워주세요.
+
+필수 값:
+
+- `OPENAI_API_KEY`
+
+### 방법 B: Streamlit secrets 사용(권장)
+
+`.streamlit/secrets.toml.example`를 복사해 `.streamlit/secrets.toml`을 만들고 값을 채워주세요.
+
+필수 값:
+
+- `OPENAI_API_KEY`
+- `GDRIVE_DB_URL` (Chroma DB zip 다운로드 링크)
+
+## 3) 실행
+
+```bash
+streamlit run main.py
+```
+
+## 동작 흐름
+
+1. 사용자가 질문 입력
+2. `moderation_utils.py`에서 유해성 검사
+3. 통과 시 `recommender.py`에서 카드 문서 검색/리랭킹
+4. `prompts.py`에서 LLM 답변 생성
+5. `main.py`에서 카드 TOP3 이미지/혜택 UI 렌더링
+
+## 참고
+
+- 최초 실행 시 `utils_db.py`가 Chroma DB zip을 다운로드/압축해제합니다.
+- 앱은 `st.secrets` 우선, 없으면 `.env`를 fallback으로 사용합니다.

