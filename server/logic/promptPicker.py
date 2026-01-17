"""
Prompt picker
- Loads prompts from backend/data/prompts.json
- Rotates categories across the 5 categories (values, emotions, identity, growth, relationships)
- Picks a deterministic prompt for a given date (stable for the whole day)

Usage:
    from datetime import date
    prompt = get_prompt_for_date(date.today())
    {"id": "...", "category": "...", "prompt": "..."}
"""

import json
from pathlib import Path
from datetime import date
from typing import Dict, List, Any

#--- Constants ---
CATEGORIES: List[str] = ["values", "emotions", "identity", "growth", "relationships"]

# Resolve path to prompts.json
PROMPTS_PATH = Path(__file__).resolve().parents[1] / "data" / "prompts.json"


# --- Load prompts ---
def _load_prompts_by_category() -> Dict[str, List[Dict[str, Any]]]:
    if not PROMPTS_PATH.exists():
        raise FileNotFoundError(f"prompts.json not found at: {PROMPTS_PATH}")

    data = json.loads(PROMPTS_PATH.read_text(encoding="utf-8"))

    # Basic validation and normalization
    prompts_by_cat: Dict[str, List[Dict[str, Any]]] = {}
    for cat in CATEGORIES:
        items = data.get(cat, [])
        if not isinstance(items, list) or len(items) == 0:
            raise ValueError(f"Category '{cat}' missing or empty in prompts.json")

        normalized = []
        for item in items:
            pid = item.get("id")
            text = item.get("prompt")
            if not pid or not text:
                raise ValueError(f"Invalid prompt item in category '{cat}': {item}")
            normalized.append({"id": pid, "prompt": text})

        prompts_by_cat[cat] = normalized

    return prompts_by_cat


PROMPTS_BY_CATEGORY = _load_prompts_by_category()


# --- Helpers ---
def _days_since_epoch(d: date) -> int:
    # date.toordinal() is deterministic and avoids timezone issues
    # (ordinal is days since 0001-01-01)
    return d.toordinal()


def _category_for_date(d: date) -> str:
    """
    Category rotation across 5 categories.
    Example: values -> emotions -> identity -> growth -> relationships -> repeat
    """
    idx = _days_since_epoch(d) % len(CATEGORIES)
    return CATEGORIES[idx]


def _prompt_index_for_date(d: date, category: str) -> int:
    """
    Deterministic prompt index within the chosen category.
    This ensures a different prompt each time the category comes around.

    We use "cycle number" so that:
      - Day-to-day category rotates.
      - When a category repeats after 5 days, you move to the next prompt in that category.
    """
    day_num = _days_since_epoch(d)
    cycle_num = day_num // len(CATEGORIES)  # increments every 5 days
    prompts = PROMPTS_BY_CATEGORY[category]
    return cycle_num % len(prompts)


# --- Public API ---
def get_prompt_for_date(d: date) -> Dict[str, Any]:
    """
    Returns:
      {"id": "...", "category": "...", "prompt": "..."}
    """
    category = _category_for_date(d)
    idx = _prompt_index_for_date(d, category)
    chosen = PROMPTS_BY_CATEGORY[category][idx]

    return {
        "id": chosen["id"],
        "category": category,
        "prompt": chosen["prompt"],
    }


def get_prompt_for_today() -> Dict[str, Any]:
    return get_prompt_for_date(date.today())
