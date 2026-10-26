"""
Tamil (or English) explanation of a post-harvest recommendation,
powered by Muse Spark. Falls back to None if the model is unavailable
or invents numbers not present in the facts.
"""
import json
import re
from typing import Optional

from app.services.meta_ai import ask_text, MetaAIUnavailable

LANGS = {"ta": "Tamil", "en": "English"}
_NUM = re.compile(r"\d[\d,]*\.?\d*")


def _numbers(s: str) -> set:
    nums = set()
    for x in _NUM.findall(s):
        try:
            nums.add(round(float(x.replace(",", "").rstrip("."))))
        except ValueError:
            pass
    return nums


def explain(facts: dict, lang: str = "ta") -> Optional[str]:
    lang_name = LANGS.get(lang, "Tamil")
    system = (
        f"You advise a smallholder farmer in simple, warm {lang_name}, in at most 5 short sentences. "
        "Use ONLY the facts given. Copy every number exactly, using digits 0-9. "
        "Say what to sell today, what to store, what to process and what is at risk. "
        "Never invent prices or places."
    )
    facts_str = json.dumps(facts, ensure_ascii=False)
    try:
        text = ask_text(system, facts_str)
    except MetaAIUnavailable:
        return None

    # Guardrail: ensure model does not fabricate numbers outside facts
    generated_nums = _numbers(text)
    allowed_nums = _numbers(facts_str)
    if not generated_nums.issubset(allowed_nums):
        return None  # The model hallucinated a number
    return text
