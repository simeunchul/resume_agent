"""PDF 페이지 수 세기. pypdf 우선, 실패 시 바이트 스캔으로 폴백."""
from __future__ import annotations

import re
from pathlib import Path

# '/Type /Pages' 가 '/Type /Page' 로 오인되지 않도록 뒤에 s 가 오면 제외
_PAGE_RE = re.compile(rb"/Type\s*/Page(?![s])")


def count_pages(pdf_path: str | Path) -> int:
    p = Path(pdf_path)
    if not p.exists():
        raise FileNotFoundError(p)
    try:
        from pypdf import PdfReader
        return len(PdfReader(str(p)).pages)
    except Exception:  # noqa: BLE001 - 손상 PDF 여도 대략치는 알아야 한다
        return len(_PAGE_RE.findall(p.read_bytes()))
