"""슬롯 → HTML. LLM 은 슬롯 JSON 만 만들고, HTML 조립은 여기서만 한다."""
from __future__ import annotations

from pathlib import Path

from jinja2 import Environment, FileSystemLoader, StrictUndefined

from ..config import TEMPLATE_DIR


def _env() -> Environment:
    return Environment(
        loader=FileSystemLoader(str(TEMPLATE_DIR)),
        undefined=StrictUndefined,   # 슬롯 누락을 조용히 넘기지 않는다
        autoescape=False,            # bullet 에 <b> 태그가 들어간다
        trim_blocks=False,
        lstrip_blocks=False,
    )


DEFAULTS = {
    "company": "",
    "job_title": "",
    "show_overseas": False,
    "career_first": False,
    "side_projects": [],
}


def render_html(slots: dict) -> str:
    ctx = {**DEFAULTS, **slots}
    return _env().get_template("resume.j2.html").render(**ctx)


def write_html(slots: dict, out_path: Path) -> Path:
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(render_html(slots), encoding="utf-8")
    return out_path
