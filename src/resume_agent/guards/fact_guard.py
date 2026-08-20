"""팩트 가드 — LLM 없이 결정적으로 검사한다 (fail-closed).

사람이 안 보는 완전 자동 모드에서 잘못된 수치가 PDF 까지 가는 것을 막는 유일한 장치.
근거 코퍼스 자체가 오염돼 있으므로(사례모음집에 92개 DAG·0.0065→0.972 잔존)
생성물 쪽에서 반드시 한 번 더 거른다.
"""
from __future__ import annotations

import io
import re
from dataclasses import dataclass, field
from pathlib import Path

import yaml

from ..config import PROFILE_DIR

# 숫자 + 단위 형태를 잡는다. '3계층', '1/3', '4.7배', '1,200만' 등
_UNITS = r"(?:만|억|배|초|개|건|차원|%|시간|일|분|층|단|회|명|점|년|월|주|GB|MB|[Bb](?![a-zA-Z]))"
_NUM_UNIT = re.compile(rf"\d[\d,\.]*\s*{_UNITS}")
_RATIO = re.compile(r"\b\d+\s*/\s*\d+\b")
_DECIMAL = re.compile(r"\b\d+\.\d+\b")
_BIGNUM = re.compile(r"\b\d{1,3}(?:,\d{3})+\b")
_TAG = re.compile(r"<[^>]+>")

# 경력 연차 부풀리기 탐지
_CAREER_WORD = re.compile(r"경력|실무\s*경험|업무\s*경험|재직|근무\s*경험")
_YEARS = re.compile(r"\d+\s*년(?!\s*\d{1,2}\s*월)")      # '2024년 2월' 같은 날짜는 제외
_NYEAR_CHA = re.compile(r"\d+\s*년\s*차")
_JD_QUOTE = re.compile(r"요건|요구|공고|필수|자격|기준|명시|채용|모집|이상을|우대")

# 문맥상 수치 주장이 아닌 것 (구조 설명)
_STRUCTURAL_OK = {
    "3계층", "3층", "3단", "2~4개", "0건", "0행", "1.0", "0명", "1건", "24시간",
    "1장", "3인", "1", "2", "3", "0",
}


def _norm(s: str) -> str:
    return re.sub(r"\s+", "", s)


@dataclass
class Violation:
    kind: str          # banned | unverified | role | missing
    token: str
    where: str
    detail: str = ""

    def __str__(self) -> str:
        d = f" — {self.detail}" if self.detail else ""
        return f"[{self.kind}] '{self.token}' ({self.where}){d}"


@dataclass
class GuardResult:
    violations: list[Violation] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.violations

    def report(self) -> str:
        if self.ok:
            return "팩트 가드 통과"
        return "\n".join(f"  {v}" for v in self.violations)


class FactGuard:
    def __init__(self, facts_path: Path | None = None):
        p = facts_path or (PROFILE_DIR / "facts.yaml")
        data = yaml.safe_load(io.open(p, encoding="utf-8"))
        self.banned = data.get("banned") or []
        allowed: set[str] = set()
        for f in data.get("facts") or []:
            for n in f.get("numbers") or []:
                allowed.add(_norm(str(n)))
        for n in (data.get("structural") or {}).get("numbers") or []:
            allowed.add(_norm(str(n)))
        allowed |= {_norm(x) for x in _STRUCTURAL_OK}
        self.allowed = allowed

    # ── 개별 검사 ───────────────────────────────────────────────────
    def _check_banned(self, text: str, where: str) -> list[Violation]:
        out = []
        for b in self.banned:
            pat = str(b.get("pattern", ""))
            if pat and pat in text:
                rep = b.get("replace_with")
                detail = b.get("reason", "")
                if rep:
                    detail += f" → '{rep}' 로 쓸 것"
                out.append(Violation("banned", pat, where, detail))
        return out

    @staticmethod
    def numbers_in(text: str) -> set[str]:
        """텍스트에 등장하는 수치 토큰. 공고 원문에서 인용 허용 목록을 만들 때 쓴다."""
        plain = _TAG.sub("", text or "")
        found: set[str] = set()
        for rx in (_NUM_UNIT, _RATIO, _DECIMAL, _BIGNUM):
            found |= {_norm(m) for m in rx.findall(plain)}
        return found

    def _check_numbers(self, text: str, where: str, extra: set[str] | None = None) -> list[Violation]:
        found = self.numbers_in(text)
        allowed = self.allowed | (extra or set())
        out = []
        for tok in sorted(found):
            if tok in allowed:
                continue
            # '1,200만' 처럼 큰수+단위가 함께 잡힌 경우 부분 일치 허용
            if any(tok in a or a in tok for a in allowed if len(a) > 2):
                continue
            out.append(Violation("unverified", tok, where, "facts.yaml 에 없는 수치"))
        return out

    def _check_career(self, text: str, where: str) -> list[Violation]:
        """경력 연차 부풀리기 차단.

        정규 경력은 서버팀 10개월뿐이고 우체국 16개월은 고용이 아니다.
        둘을 합쳐 'n년 경력'이라고 쓰면 허위 기재다. 프롬프트로만 막으면 새므로
        여기서 결정적으로 잡는다. JD 요건을 인용하는 문장은 통과시킨다.
        """
        out = []
        plain = _TAG.sub("", text)
        for sent in re.split(r"(?<=[.。!?])\s+|／|\n", plain):
            if not sent.strip():
                continue
            if _NYEAR_CHA.search(sent):
                out.append(Violation("career", _NYEAR_CHA.search(sent).group(0), where,
                                     "정규 경력은 서버팀 10개월이다. 연차를 주장하지 않는다"))
                continue
            if not (_CAREER_WORD.search(sent) and _YEARS.search(sent)):
                continue
            if "10개월" in sent or "16개월" in sent:
                continue                       # 정확히 표기한 경우
            if _JD_QUOTE.search(sent):
                continue                       # JD 요건을 인용하는 문장
            out.append(Violation("career", _YEARS.search(sent).group(0), where,
                                 "정규 경력은 서버팀 10개월. 우체국 16개월은 경력이 아니다"))
        return out

    def _check_role(self, slots: dict) -> list[Violation]:
        """'혼자/단독' 은 운영 감사 에이전트에만 붙일 수 있다."""
        out = []
        for i, b in enumerate(slots.get("blocks") or []):
            body = " ".join([b.get("title", ""), *(b.get("bullets") or [])])
            body = _TAG.sub("", body)
            if re.search(r"혼자|단독", body) and not re.search(r"운영\s*감사|감사\s*에이전트", body):
                out.append(Violation("role", "혼자/단독", f"blocks[{i}] {b.get('title','')}",
                                     "'혼자·단독'은 운영 감사 에이전트에만 붙인다"))
        return out

    def _check_required(self, slots: dict) -> list[Violation]:
        out = []
        if not slots.get("not_yet_chips"):
            out.append(Violation("missing", "점선칩", "not_yet_chips",
                                 "'아직 다뤄보지 않은 것' 그룹은 필수"))
        note = _TAG.sub("", slots.get("honesty_note") or "")
        if len(note) < 60:
            out.append(Violation("missing", "정직 표기", "honesty_note",
                                 "정직 표기 note 가 비었거나 너무 짧다"))
        elif not note.startswith("정직하게"):
            out.append(Violation("missing", "시작구", "honesty_note",
                                 "'정직하게 밝힙니다 —' 로 시작해야 한다"))
        elif not re.search(r"현장 프로젝트형|정규 (고용|경력)", note):
            out.append(Violation("missing", "참여 형태", "honesty_note",
                                 "참여 형태(현장 프로젝트형 / 정규 경력 10개월)를 밝혀야 한다"))
        for i, c in enumerate(slots.get("core") or []):
            if not c.get("title") or not c.get("body"):
                out.append(Violation("missing", f"core[{i}]", "core", "제목 또는 본문 누락"))
        return out

    # ── 진입점 ─────────────────────────────────────────────────────
    def check(self, slots: dict, jd_text: str = "") -> GuardResult:
        """jd_text 를 주면 공고 원문에 있는 수치는 '인용' 으로 허용한다.

        정직 표기에서 "3년 이상을 요구하는 요건에 저는 미달합니다" 라고 쓰는 것은 정당하다.
        그 수치를 본인 경력처럼 주장하는 경우는 _check_career 가 따로 잡는다.
        """
        quoted = self.numbers_in(jd_text) if jd_text else set()
        vs: list[Violation] = []
        targets: list[tuple[str, str]] = [
            ("tagline", slots.get("tagline", "")),
            ("honesty_note", slots.get("honesty_note", "")),
        ]
        for i, c in enumerate(slots.get("core") or []):
            targets.append((f"core[{i}]", f"{c.get('title','')} {c.get('body','')}"))
        for i, b in enumerate(slots.get("blocks") or []):
            targets.append((f"blocks[{i}].title", b.get("title", "")))
            for j, li in enumerate(b.get("bullets") or []):
                targets.append((f"blocks[{i}].bullets[{j}]", li))
        for i, s in enumerate(slots.get("side_projects") or []):
            targets.append((f"side[{i}]", f"{s.get('title','')} {s.get('text','')}"))

        for where, text in targets:
            if not text:
                continue
            vs += self._check_banned(text, where)
            vs += self._check_numbers(text, where, quoted)
            vs += self._check_career(text, where)
        vs += self._check_role(slots)
        vs += self._check_required(slots)
        return GuardResult(vs)
