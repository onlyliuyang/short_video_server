from __future__ import annotations

import logging
from functools import lru_cache
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from app.core.config import settings

logger = logging.getLogger(__name__)

PROMPTS_ROOT = Path(__file__).resolve().parent.parent / "prompts"


def _prompts_dir() -> Path:
    custom = getattr(settings, "prompt_dir", None) or getattr(settings, "PROMPT_DIR", None)
    if custom:
        p = Path(custom)
        if p.is_dir():
            return p
    return PROMPTS_ROOT


def _env() -> Environment:
    return Environment(
        loader=FileSystemLoader(str(_prompts_dir())),
        autoescape=select_autoescape(default=False),
        keep_trailing_newline=True,
    )


def _read_text(path: Path) -> str:
    if not path.is_file():
        raise FileNotFoundError(f"Prompt file not found: {path}")
    return path.read_text(encoding="utf-8")


@lru_cache(maxsize=128)
def _cached_system(path_key: str, mtime: float) -> str:
    return _read_text(Path(path_key))


def load_system_prompt(profile: str, mode: str) -> str:
    """Load LLM system prompt: prompts/llm/{profile}/storyboard_{mode}.system.md"""
    rel = Path("llm") / profile / f"storyboard_{mode}.system.md"
    full = _prompts_dir() / rel
    if settings.prompt_hot_reload:
        return _read_text(full)
    return _cached_system(str(full), full.stat().st_mtime if full.exists() else 0)


def render_user_prompt(profile: str, mode: str, **ctx) -> str:
    """Render LLM user prompt: prompts/llm/{profile}/storyboard_{mode}.user.j2"""
    rel = f"llm/{profile}/storyboard_{mode}.user.j2"
    return _env().get_template(rel).render(**ctx)


def render_segment_prompt(profile: str, template_name: str, **ctx) -> str:
    """Render segment prompt: prompts/segment/{profile}/{template_name}.j2"""
    rel = f"segment/{profile}/{template_name}.j2"
    return _env().get_template(rel).render(**ctx)


def load_retry_suffix(profile: str, mode: str) -> str:
    path = _prompts_dir() / "llm" / profile / f"storyboard_{mode}.retry_suffix.txt"
    if path.is_file():
        return path.read_text(encoding="utf-8").strip()
    return "上次输出格式有误。请仅返回一个合法 JSON 对象，首尾不要有任何其他字符。"
