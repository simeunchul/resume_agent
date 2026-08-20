"""HTML → PDF (Edge headless).

Playwright 가 있어도 PDF 는 Edge 로 뽑는다. 기존 이력서 PDF 가 전부 Edge 출력이라
렌더러를 바꾸면 폰트 메트릭이 달라져 2페이지 경계가 흔들린다.

과거에 실패했던 원인 두 가지를 코드로 막는다:
  1. 남아 있는 msedge 프로세스 → 먼저 정리
  2. --user-data-dir 폴더 부재 → 미리 만들어 둔다
"""
from __future__ import annotations

import shutil
import subprocess
import tempfile
import uuid
from pathlib import Path

EDGE_CANDIDATES = [
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
]


def _edge() -> str:
    for c in EDGE_CANDIDATES:
        if Path(c).exists():
            return c
    found = shutil.which("msedge")
    if found:
        return found
    raise FileNotFoundError("msedge.exe 를 찾지 못했습니다")


def _kill_edge() -> None:
    """물려 있는 Edge 를 먼저 정리하지 않으면 PDF 가 조용히 안 나온다."""
    subprocess.run(
        ["taskkill", "/F", "/IM", "msedge.exe", "/T"],
        capture_output=True, check=False,
    )


def html_to_pdf(html_path: str | Path, pdf_path: str | Path, timeout: int = 120) -> Path:
    html_path, pdf_path = Path(html_path).resolve(), Path(pdf_path).resolve()
    if not html_path.exists():
        raise FileNotFoundError(html_path)
    pdf_path.parent.mkdir(parents=True, exist_ok=True)

    _kill_edge()

    tmp_root = Path(tempfile.gettempdir()) / f"resume_agent_{uuid.uuid4().hex[:8]}"
    profile_dir = tmp_root / "profile"
    profile_dir.mkdir(parents=True, exist_ok=True)      # ← 없으면 조용히 실패한다
    staged_pdf = tmp_root / "out.pdf"                   # 기존 PDF 덮어쓰기 회피

    args = [
        _edge(),
        "--headless=new", "--disable-gpu", "--no-first-run", "--no-default-browser-check",
        "--disable-background-networking", "--disable-sync",
        f"--user-data-dir={profile_dir}",
        "--virtual-time-budget=20000",
        "--no-pdf-header-footer",
        f"--print-to-pdf={staged_pdf}",
        html_path.as_uri(),
    ]
    try:
        subprocess.run(args, capture_output=True, timeout=timeout, check=False)
        if not staged_pdf.exists() or staged_pdf.stat().st_size == 0:
            raise RuntimeError(f"PDF 생성 실패 — {staged_pdf} 가 비어 있음")
        shutil.copyfile(staged_pdf, pdf_path)           # Copy-Item -Force 에 해당
    finally:
        _kill_edge()
        shutil.rmtree(tmp_root, ignore_errors=True)
    return pdf_path
