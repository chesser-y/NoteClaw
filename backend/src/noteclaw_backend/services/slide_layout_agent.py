"""Layout Agent for PPT slides.

Given a slide outline, decides which HTML template to use and how much text fits.
Output drives the HTML renderer.
"""
from __future__ import annotations

import logging
from typing import Any

from noteclaw_backend.services.providers import get_llm_provider

logger = logging.getLogger(__name__)

TEMPLATES = ("title", "bullets", "two_column", "quote")


async def decide_slide_layouts(slides: list[dict[str, Any]], deck_title: str = "") -> list[dict[str, Any]]:
    """One LLM call: decide layout for each slide.

    Returns one decision per input slide:
        {
            "template": "title" | "bullets" | "two_column" | "quote",
            "text_budget": int,         # max chars for body text
            "body_size": int,           # font-size px hint for bullets
            "params": {                 # template-specific extras
                "left_title": str, "right_title": str,
                "left_items": [str], "right_items": [str],
                "subtitle": str, "author": str, "attribution": str, ...
            }
        }
    Falls back to a heuristic when LLM is unavailable or output malformed.
    """
    if not slides:
        return []

    try:
        decisions = await _llm_decide(slides, deck_title)
        if len(decisions) == len(slides):
            return [_coerce(dec, slide) for dec, slide in zip(decisions, slides)]
    except Exception as exc:  # noqa: BLE001
        logger.warning("slide_layout_agent LLM failed: %s", exc)

    return [_heuristic(slide, i, len(slides)) for i, slide in enumerate(slides)]


async def _llm_decide(slides: list[dict[str, Any]], deck_title: str) -> list[dict[str, Any]]:
    system = (
        "You are a PPT layout agent. For each slide, pick the best HTML template "
        "and decide how much text fits. Return JSON: {\"decisions\":[...]}."
    )
    catalog = (
        "Templates:\n"
        "- title: cover slide. Use for deck cover or section dividers. Params: subtitle, author.\n"
        "- bullets: standard content slide with a list. Params: body_size (px, 16-26).\n"
        "- two_column: comparison slide. Params: left_title, right_title, left_items[], right_items[].\n"
        "- quote: highlight a single quotation. Params: attribution.\n"
        "Constraints: 1280x720 canvas. Keep body_size 18-24 if many bullets; up to 26 if few."
    )
    payload = [
        {"role": "system", "content": f"{system}\n\n{catalog}"},
        {
            "role": "user",
            "content": (
                f"Deck: {deck_title}\n"
                f"Slides ({len(slides)}):\n"
                + _serialize_slides(slides)
                + "\nReturn JSON {\"decisions\": [ {template, text_budget, body_size, params}, ... ]} "
                "aligned with the input order. Use two_column only when the slide compares two sides."
            ),
        },
    ]
    data = await get_llm_provider().complete_json(payload)
    decisions = data.get("decisions") if isinstance(data, dict) else None
    if not isinstance(decisions, list):
        return []
    return decisions


def _serialize_slides(slides: list[dict[str, Any]]) -> str:
    lines = []
    for i, slide in enumerate(slides):
        title = str(slide.get("title") or "")[:80]
        layout = str(slide.get("layout") or "")
        bullets = slide.get("bullets") or slide.get("points") or []
        if isinstance(bullets, str):
            bullets = [bullets]
        bullets_str = " | ".join(str(b)[:60] for b in bullets[:5])
        lines.append(f"{i + 1}. [{layout}] {title} :: {bullets_str}")
    return "\n".join(lines)


def _coerce(decision: dict[str, Any], slide: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(decision, dict):
        return _heuristic(slide, 0, 1)
    template = str(decision.get("template") or "").strip().lower()
    if template not in TEMPLATES:
        template = "bullets"
    text_budget = _clamp_int(decision.get("text_budget"), 200, 1200, 600)
    body_size = _clamp_int(decision.get("body_size"), 14, 30, 22)
    params = decision.get("params") if isinstance(decision.get("params"), dict) else {}
    return {
        "template": template,
        "text_budget": text_budget,
        "body_size": body_size,
        "params": params,
    }


def _heuristic(slide: dict[str, Any], index: int, total: int) -> dict[str, Any]:
    layout = str(slide.get("layout") or "").lower()
    bullets = slide.get("bullets") or slide.get("points") or []
    if isinstance(bullets, str):
        bullets = [bullets]
    bullet_count = len(bullets)

    if index == 0 or layout in {"cover", "title"}:
        return {
            "template": "title",
            "text_budget": 200,
            "body_size": 24,
            "params": {"subtitle": slide.get("subtitle") or ""},
        }
    if layout in {"summary", "takeaways"} or bullet_count <= 1:
        return {
            "template": "quote",
            "text_budget": 360,
            "body_size": 22,
            "params": {"attribution": ""},
        }
    if bullet_count >= 4 and any(_looks_comparison(b) for b in bullets):
        halves = _split_comparison(bullets)
        return {
            "template": "two_column",
            "text_budget": 600,
            "body_size": 18,
            "params": {
                "left_title": "Aspect A",
                "right_title": "Aspect B",
                "left_items": halves[0],
                "right_items": halves[1],
            },
        }
    body_size = 24 if bullet_count <= 3 else 20
    return {
        "template": "bullets",
        "text_budget": 800,
        "body_size": body_size,
        "params": {},
    }


def _looks_comparison(text: Any) -> bool:
    s = str(text).lower()
    return any(cue in s for cue in ("vs", "versus", "对比", "相比", "pros", "cons", "不同于"))


def _split_comparison(bullets: list[Any]) -> tuple[list[str], list[str]]:
    half = max(1, len(bullets) // 2)
    left = [str(b)[:120] for b in bullets[:half]]
    right = [str(b)[:120] for b in bullets[half:]]
    return left or ["—"], right or ["—"]


def _clamp_int(value: Any, low: int, high: int, default: int) -> int:
    try:
        v = int(value)
    except (TypeError, ValueError):
        return default
    return max(low, min(high, v))
