"""Shared storyboard JSON parsing and post-processing."""

from __future__ import annotations

import json
import logging
import re

logger = logging.getLogger(__name__)


def strip_markdown_fence(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.IGNORECASE)
        text = re.sub(r"\s*```\s*$", "", text)
    return text.strip()


def extract_json(text: str) -> dict:
    text = strip_markdown_fence(text)
    decoder = json.JSONDecoder()

    search_from = 0
    last_error: Exception | None = None
    while search_from < len(text):
        start = text.find("{", search_from)
        if start < 0:
            break
        try:
            data, end = decoder.raw_decode(text, start)
            if isinstance(data, dict):
                if end < len(text) and text[end:].strip():
                    logger.warning(
                        "LLM JSON had trailing content after char %d, ignored: %s",
                        end, text[end : end + 200],
                    )
                return data
        except json.JSONDecodeError as e:
            last_error = e
            search_from = start + 1
            continue
        search_from = start + 1

    match = re.search(r"\{[\s\S]*\}", text)
    if match:
        try:
            data, _ = decoder.raw_decode(match.group(), 0)
            if isinstance(data, dict):
                return data
        except json.JSONDecodeError as e:
            last_error = e

    preview = text[:800] + ("..." if len(text) > 800 else "")
    raise ValueError(
        f"LLM response does not contain valid JSON: {last_error}. Preview: {preview}"
    )


def enforce_setting_anchor(script_data: dict, user_prompt: str) -> dict:
    anchor = (script_data.get("setting_anchor") or "").strip()
    keywords: list[str] = script_data.get("setting_keywords") or []

    if not anchor:
        anchor = user_prompt.strip()

    if not keywords and anchor:
        if any("\u4e00" <= c <= "\u9fff" for c in anchor):
            keywords = [anchor]
        else:
            keywords = [w for w in anchor.replace(",", " ").split() if len(w) > 2][:8]

    script_data["setting_anchor"] = anchor
    script_data["setting_keywords"] = keywords

    prefix = anchor
    if keywords:
        kw = ", ".join(keywords[:8])
        prefix = f"{anchor}. Required elements: {kw}"

    def _anchor_present(sp: str) -> bool:
        sp_lower = sp.lower()
        if anchor in sp or anchor.lower() in sp_lower:
            return True
        return any(k in sp or k.lower() in sp_lower for k in keywords)

    for seg in script_data.get("segments", []):
        sp = (seg.get("scene_prompt") or "").strip()
        if not sp or not _anchor_present(sp):
            seg["scene_prompt"] = f"{prefix}. {sp}" if sp else prefix
            logger.info(
                "[LLM] enforced setting on seg=%s anchor=%s",
                seg.get("index"), anchor[:60],
            )
        ip = (seg.get("image_prompt") or "").strip()
        if not ip or not _anchor_present(ip):
            seg["image_prompt"] = f"{prefix}. {ip}" if ip else prefix
    return script_data
