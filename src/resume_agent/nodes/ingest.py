"""공고 읽기 — 텍스트가 나오면 텍스트로, 안 나오면 스크린샷 + VLM.

'드래그가 안 되는 공고'(본문이 이미지)를 위한 경로가 여기 들어 있다.
별도 OCR 엔진이 아니라 VLM 으로 읽는다 — 한국어 공고 이미지에서 더 정확하고
표·박스 레이아웃도 같이 이해한다.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from playwright.sync_api import sync_playwright

from ..config import MIN_JD_TEXT_LEN, USER_AGENT

# 실제 JD 본문에만 나오는 강한 신호 — 이게 없으면 본문을 못 읽은 것이다
STRONG_HINTS = ["담당업무", "주요업무", "업무 내용", "수행업무", "자격요건", "자격 요건",
                "우대사항", "우대 사항", "이런 분", "필수 요건", "자격 조건"]
# 목록 페이지 껍데기에도 흔히 나오는 약한 신호 (단독으로는 신뢰하지 않는다)
WEAK_HINTS = ["지원자격", "모집분야", "모집요강", "우대조건", "근무조건"]

SLICE_H = 2000        # 스크린샷 분할 높이
MAX_SLICES = 8        # VLM 비용 상한
EXPAND_LABELS = ["상세 정보 더 보기", "더 보기", "펼쳐보기", "상세요강", "더보기"]


@dataclass
class Ingested:
    url: str
    text: str = ""
    images: list[bytes] = field(default_factory=list)
    mode: str = "text"          # text | image
    error: str = ""

    @property
    def ok(self) -> bool:
        return bool(self.text.strip() or self.images)


def _looks_complete(text: str) -> bool:
    """강한 신호 2개 이상이어야 본문을 읽은 것으로 인정한다.

    잡코리아처럼 껍데기에 '지원자격·모집분야'만 있고 정작 상세요강은
    이미지 iframe 에 있는 경우를 약한 신호만으로 통과시키면 안 된다.
    """
    if len(text) < MIN_JD_TEXT_LEN:
        return False
    return sum(1 for h in STRONG_HINTS if h in text) >= 2


def _force_lazy_load(page) -> None:
    """지연 로딩 이미지를 강제로 띄운다.

    스크롤 없이 clip 으로 찍으면 화면 아래 이미지는 아직 로드되지 않아 빈칸으로 나온다.
    이미지형 공고에서는 이게 곧 '아무것도 못 읽음' 이 된다.
    """
    page.evaluate("""async () => {
        const step = 800;
        for (let y = 0; y < document.body.scrollHeight; y += step) {
            window.scrollTo(0, y);
            await new Promise(r => setTimeout(r, 120));
        }
        document.querySelectorAll('img[loading="lazy"]').forEach(e => e.loading = 'eager');
        document.querySelectorAll('img[data-src]').forEach(e => {
            if (!e.src || e.src.startsWith('data:')) e.src = e.dataset.src;
        });
        window.scrollTo(0, 0);
    }""")
    page.wait_for_timeout(2500)


def _slice_screenshots(page) -> list[bytes]:
    """긴 페이지를 조각내 찍는다. 통짜 full_page 는 너무 커서 VLM 에 못 넣는다."""
    _force_lazy_load(page)
    total = page.evaluate(
        "() => Math.max(document.body.scrollHeight, document.documentElement.scrollHeight)")
    width = page.viewport_size["width"]
    shots: list[bytes] = []
    y = 0
    while y < total and len(shots) < MAX_SLICES:
        h = min(SLICE_H, total - y)
        if h <= 0:
            break
        try:
            # clip 은 뷰포트 기준이라, 화면 밖까지 자르려면 full_page 를 함께 켜야 한다
            shots.append(page.screenshot(
                clip={"x": 0, "y": y, "width": width, "height": h}, full_page=True))
        except Exception as e:  # noqa: BLE001 - 조각 하나가 실패해도 나머지는 건진다
            print(f"    [ingest] 스크린샷 조각 실패 (y={y}): {type(e).__name__}")
        y += h
    return shots


def ingest(url: str, timeout: int = 60000, force_image: bool = False) -> Ingested:
    out = Ingested(url=url)
    try:
        with sync_playwright() as pw:
            br = pw.chromium.launch(headless=True)
            ctx = br.new_context(user_agent=USER_AGENT, locale="ko-KR",
                                 viewport={"width": 1440, "height": 1200})
            pg = ctx.new_page()
            try:
                pg.goto(url, wait_until="domcontentloaded", timeout=timeout)
                pg.wait_for_timeout(3500)

                # 접혀 있는 상세 내용을 편다
                for label in EXPAND_LABELS:
                    try:
                        btn = pg.get_by_role("button", name=label)
                        if btn.count():
                            btn.first.click(timeout=2500)
                            pg.wait_for_timeout(1200)
                    except Exception:  # noqa: BLE001 - 버튼이 없거나 안 눌려도 진행
                        pass

                text = pg.inner_text("body")

                # 본문이 별도 iframe 에 있는 경우 (잡코리아 상세요강 등)
                for f in pg.frames[1:]:
                    try:
                        ft = f.inner_text("body")
                        if len(ft) > 200:
                            text += "\n" + ft
                    except Exception:  # noqa: BLE001
                        pass

                if _looks_complete(text) and not force_image:
                    out.text, out.mode = text, "text"
                else:
                    # 드래그가 안 되는 공고 — 이미지로 읽는다
                    out.text = text
                    out.images = _slice_screenshots(pg)
                    out.mode = "image"
            finally:
                br.close()
    except Exception as e:  # noqa: BLE001 - 공고 하나가 죽어도 배치는 계속
        out.error = f"{type(e).__name__}: {e}"
    return out
