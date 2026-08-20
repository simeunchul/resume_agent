"""공고 텍스트/이미지 → JD 구조체."""
from __future__ import annotations

from ..llm import MODEL_READ, generate_json
from ..nodes.ingest import Ingested
from ..schemas import JD

PROMPT_TEXT = """다음은 채용 공고 페이지에서 긁어온 텍스트다.
네비게이션·푸터·추천공고·광고 같은 잡음이 섞여 있으니 **이 공고 본문에 해당하는 것만** 추려라.

규칙:
- 담당업무 / 자격요건(필수) / 우대사항을 구분해서 담아라. 공고가 구분하지 않았으면 내용으로 판단해라.
- 원문 표현을 최대한 유지하고 요약하지 마라. 한 항목이 한 줄이다.
- 회사명에서 (주)·㈜·주식회사 같은 법인격 표기는 뺀다.
- 없는 항목은 빈 배열로 둔다. 지어내지 마라.

--- 공고 텍스트 ---
{text}
"""

PROMPT_IMAGE = """첨부한 이미지들은 채용 공고 상세 페이지를 위에서 아래로 잘라 찍은 것이다.
이미지 안의 글자를 읽어 공고 내용을 구조화해라.

규칙:
- 담당업무 / 자격요건(필수) / 우대사항을 구분해서 담아라.
- 이미지에 적힌 표현을 그대로 옮겨라. 읽히지 않는 부분은 넣지 마라.
- 회사명에서 (주)·㈜·주식회사 같은 법인격 표기는 뺀다.
- 없는 항목은 빈 배열로 둔다.

참고로 같은 페이지에서 긁은 텍스트(불완전할 수 있음)는 아래와 같다:
--- 참고 텍스트 ---
{text}
"""


# 공고 껍데기의 메타데이터. 진짜 자격요건이 아니다.
_JUNK_REQ = ("경력무관", "학력무관", "대졸이상", "고졸이상", "초대졸이상", "학력무관",
             "신입·경력", "신입/경력", "무관", "상세요강 참조", "직무별상이")


def _real_reqs(items: list[str]) -> list[str]:
    out = []
    for x in items:
        t = x.replace(" ", "")
        if len(t) <= 12 and any(j.replace(" ", "") in t for j in _JUNK_REQ):
            continue
        out.append(x)
    return out


def _thin(jd: JD | None) -> bool:
    """본문을 못 읽으면 담당업무나 자격요건 한쪽이 반드시 비어 있다.

    둘 다 비어야 thin 으로 보면, 껍데기의 '경력무관/학력무관' 두 줄에 속는다.
    진짜 공고는 담당업무와 자격요건이 둘 다 2개 이상이다.
    """
    if jd is None:
        return True
    return len(jd.responsibilities) < 2 or len(_real_reqs(jd.requirements)) < 2


def parse_jd_with_fallback(url: str) -> tuple[JD | None, Ingested]:
    """텍스트로 먼저 읽고, 결과가 빈약하면 이미지로 다시 읽는다.

    휴리스틱(섹션 키워드)만으로는 '껍데기는 텍스트, 본문은 이미지'인 공고를
    걸러내지 못한다. 파싱 결과를 보고 판단하는 쪽이 확실하다.
    """
    from ..nodes.ingest import ingest
    ing = ingest(url)
    jd = parse_jd(ing) if ing.ok else None
    if not _thin(jd) or ing.mode == "image":
        return jd, ing

    ing2 = ingest(url, force_image=True)
    if not ing2.images:
        return jd, ing
    jd2 = parse_jd(ing2)
    # 둘 다 빈약하면 그나마 내용이 많은 쪽을 쓴다
    if _richness(jd2) > _richness(jd):
        return jd2, ing2
    return jd, ing


def _richness(jd: JD | None) -> int:
    if jd is None:
        return -1
    return len(jd.responsibilities) + len(_real_reqs(jd.requirements)) + len(jd.preferred)


def parse_jd(ing: Ingested) -> JD | None:
    if not ing.ok:
        return None
    text = (ing.text or "")[:60000]
    if ing.mode == "image" and ing.images:
        result = generate_json(PROMPT_IMAGE.format(text=text[:8000]), JD,
                               model=MODEL_READ, images=ing.images)
    else:
        result = generate_json(PROMPT_TEXT.format(text=text), JD, model=MODEL_READ)
    if isinstance(result, JD):
        return result
    if isinstance(result, str):
        try:
            return JD.model_validate_json(result)
        except Exception:  # noqa: BLE001
            return None
    return None
