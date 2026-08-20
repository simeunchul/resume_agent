"""전역 설정 — 경로, 키워드, 임계값.

개인 정보와 사용자별 경로는 코드에 박지 않는다. `.env` 와 `profile/` 에서 읽는다.
`profile/` 의 실데이터는 git 에 올라가지 않는다 (`profile/example/` 만 올라간다).
"""
from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

# ── 경로 ────────────────────────────────────────────────────────────────
PKG_ROOT = Path(__file__).resolve().parent
PROJECT_ROOT = PKG_ROOT.parent.parent

load_dotenv(PROJECT_ROOT / ".env")     # config 가 가장 먼저 import 되므로 여기서 읽는다

PROFILE_DIR = PROJECT_ROOT / "profile"
PROFILE_EXAMPLE_DIR = PROFILE_DIR / "example"
TEMPLATE_DIR = PROJECT_ROOT / "templates"
RUNS_DIR = PROJECT_ROOT / "runs"
LEDGER = PROJECT_ROOT / "applications.jsonl"

# 제출 서류가 실제로 저장되는 곳 (회사별 폴더가 여기 아래 생긴다).
# .env 의 RESUME_ROOT 로 지정한다. 없으면 프로젝트 안 output/ 으로 떨어진다.
RESUME_ROOT = Path(os.getenv("RESUME_ROOT") or (PROJECT_ROOT / "output"))
COMMON_DIR = Path(os.getenv("RESUME_COMMON_DIR") or (RESUME_ROOT / "공통_프로필_포트폴리오"))
PHOTO_SRC = COMMON_DIR / "photo.jpg"          # 없으면 사진 없이 렌더한다
TEMPLATE_SRC = COMMON_DIR / "_이력서_템플릿.html"


def _owner() -> str:
    """이력서 파일명에 쓸 이름. .env 의 RESUME_OWNER > profile/projects.yaml 의 header.name"""
    env = os.getenv("RESUME_OWNER", "").strip()
    if env:
        return env
    try:
        import yaml
        with open(PROFILE_DIR / "projects.yaml", encoding="utf-8") as f:
            return str((yaml.safe_load(f).get("header") or {}).get("name") or "").strip()
    except Exception:  # noqa: BLE001 - 프로필이 아직 없으면 이름 없이 간다
        return ""


RESUME_OWNER = _owner()
RESUME_HTML_NAME = f"{RESUME_OWNER}_이력서.html" if RESUME_OWNER else "이력서.html"
RESUME_PDF_NAME = f"{RESUME_OWNER}_이력서.pdf" if RESUME_OWNER else "이력서.pdf"


def profile_text(filename: str) -> str:
    """profile/ 의 텍스트 파일을 읽는다. 없으면 무엇을 복사해야 하는지 알려주고 멈춘다."""
    p = PROFILE_DIR / filename
    if not p.exists():
        raise SystemExit(
            f"\n[!] {p} 가 없습니다.\n"
            f"    profile/example/{filename} 을 profile/{filename} 로 복사한 뒤 본인 내용으로 채우세요.\n"
        )
    return p.read_text(encoding="utf-8")

# ── 수집 키워드 ─────────────────────────────────────────────────────────
SEARCH_KEYWORDS = [
    "AI 엔지니어", "AI 개발자", "AI Agent", "LLM", "MLOps",
    "머신러닝 엔지니어", "데이터 엔지니어", "데이터 분석가",
]

# prefilter — 느슨하게 통과시키고 최종 판단은 fit_gate(LLM)에 맡긴다
RELEVANT_TERMS = [
    "ai", "인공지능", "ml", "머신러닝", "딥러닝", "llm", "mlops", "llmops",
    "agent", "에이전트", "rag", "생성형", "genai", "nlp", "자연어",
    "데이터 엔지니어", "데이터엔지니어", "data engineer",
    "데이터 분석", "데이터분석", "data analyst", "분석가",
    "데이터 사이언", "data scien", "추천", "recommend",
    "machine learning", "ml engineer", "mle", "파이프라인", "플랫폼 엔지니어",
]
# 명백히 무관한 것만 컷 (과하게 자르지 않는다)
EXCLUDE_TERMS = [
    "영업", "마케팅", "디자이너", "퍼블리셔", "회계", "인사담당", "총무",
    "ios 개발", "안드로이드 개발", "프론트엔드 개발", "publisher",
]

# ── 임계값 ──────────────────────────────────────────────────────────────
FIT_THRESHOLD = 65        # fit_gate 통과 점수 (0-100)
MIN_YEARS_BLOCK = 3       # 요구 경력 '하한'이 이 값 이상이면 결격 (본인 정규 경력 10개월)
                          #   3 = 좁게(신입~2년 공고만) / 5 = 중간 / 99 = 연차로 거르지 않음
DAILY_RESUME_CAP = 5      # 하루에 만들 이력서 최대 개수
MAX_PAGES = 2             # 이력서 페이지 수 상한
MAX_TRIM_ROUNDS = 3       # 분량 초과 시 덜어내기 재시도
MAX_FACT_RETRIES = 2      # 팩트 가드 위반 시 재작성 재시도
MIN_JD_TEXT_LEN = 400     # 이보다 짧으면 이미지 공고로 보고 스크린샷 경로로

# ── LLM ─────────────────────────────────────────────────────────────────
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "")
MODEL_READ = os.getenv("MODEL_READ", "")     # 판독·파싱 (flash 계열)
MODEL_WRITE = os.getenv("MODEL_WRITE", "")   # 작성·갭분석 (pro 계열)

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)
