"""
Insight Engine (Weekly)
- Computes lightweight signals:
  1) Most common themes (keywords)
  2) Emotional polarity (positive / neutral / negative)
  3) Repeating phrases ("I feel...", "I'm worried...", etc.)
- Then uses the Gemini API to turn those signals along with
  the week's entries into a human-friendly weekly report.

Dependencies:
  pip install google-genai

Environment:
  export GEMINI_API_KEY="..."              # Gemini Developer API key (AI Studio)
  export GEMINI_MODEL="gemini-2.5-flash"   # optional (defaults below)
"""

from __future__ import annotations

import os
import re
from collections import Counter
from typing import Any, Dict, List, Tuple
import json

try:
    # Google Gen AI SDK 
    from google import genai
    from google.genai import types
except Exception:
    genai = None
    types = None


# -----------------------------
# Lightweight signal extraction
# -----------------------------

STOPWORDS = {
    "the", "a", "an", "and", "or", "but", "to", "of", "in", "on", "for", "with", "at", "by",
    "is", "are", "was", "were", "be", "been", "it", "that", "this", "as",
    "i", "you", "we", "my", "your", "our", "me", "us", "they", "them", "he", "she", "his", "her",
    "today", "week", "really", "just", "like", "got", "get", "what", "when", "how", "so", "too",
    "not", "no", "im", "ive", "cant", "dont", "didnt", "wont", "would", "could", "should",
    "feel", "feeling", "felt", "think", "thinking", "thought", "know", "knowing", "known"
}

# Very lightweight lexicon-based sentiment analysis
# (for demo purposes; replace with a proper library for production)
POS_WORDS = {
    "calm", "good", "great", "proud", "excited", "happy", "relieved", "grateful",
    "energized", "hopeful", "confident", "peaceful", "motivated", "joyful", "content",
    "satisfied", "optimistic", "enthusiastic", "cheerful", "encouraged", "fulfilled",
}
NEG_WORDS = {
    "tired", "anxious", "worried", "sad", "angry", "overwhelmed", "stressed",
    "upset", "frustrated", "guilty", "lonely", "burnt", "burned", "disappointed",
    "discouraged", "fearful", "insecure", "nervous", "resentful", "unhappy", "uneasy", "vulnerable"
}

PHRASE_PATTERNS = [
    r"\bi feel\b",
    r"\bi'm worried\b",
    r"\bi am worried\b",
    r"\bi need\b",
    r"\bi want\b",
    r"\bi can't\b",
    r"\bi cannot\b",
    r"\bi should\b",
    r"\bi'm afraid\b",
    r"\bi am afraid\b",
]

#--- Helpers ---
#tokenize text into words, removing stopwords and short words
def _tokenize(text: str) -> List[str]:
    words = re.findall(r"[a-zA-Z']+", (text or "").lower())
    return [w for w in words if w not in STOPWORDS and len(w) >= 3]
#check polarity score based on positive and negative words
def _polarity_score(text: str) -> int:
    words = re.findall(r"[a-zA-Z']+", (text or "").lower())
    score = 0
    for w in words:
        if w in POS_WORDS:
            score += 1
        if w in NEG_WORDS:
            score -= 1
    return score
#determine polarity label based on total score
def _label_polarity(total_score: int) -> str:
    if total_score >= 2:
        return "positive"
    if total_score <= -2:
        return "negative"
    return "neutral"

def _repeating_phrases(responses: List[str]) -> List[str]:
    counts = Counter()
    joined = "\n".join(responses).lower()
    for pat in PHRASE_PATTERNS:
        matches = re.findall(pat, joined)
        if matches:
            counts[pat] += len(matches)
#map regex patterns to plain text phrases
    mapping = {
        r"\bi feel\b": "“I feel…”",
        r"\bi'm worried\b": "“I’m worried…”",
        r"\bi am worried\b": "“I’m worried…”",
        r"\bi need\b": "“I need…”",
        r"\bi want\b": "“I want…”",
        r"\bi can't\b": "“I can’t…”",
        r"\bi cannot\b": "“I can’t…”",
        r"\bi should\b": "“I should…”",
        r"\bi'm afraid\b": "“I’m afraid…”",
        r"\bi am afraid\b": "“I’m afraid…”",
    }

    return [mapping[k] for k, _ in counts.most_common(3)]

#--- Main extraction function ---
def _extract_signals(entries: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    entries expected shape:
      { "prompt": str, "response": str, "timestamp": int }
    """
    # IMPORTANT: We deliberately compute theme signals primarily from *responses* (not prompts)
    # so the final themes reflect the user's writing, not the app's prompt wording.
    responses = [(e.get("response") or "").strip() for e in entries]
    texts = [r for r in responses if r]

    tokens: List[str] = []
    polarity_total = 0

    for t in texts:
        tokens.extend(_tokenize(t))
        polarity_total += _polarity_score(t)

    theme_counts = Counter(tokens)
    themes = [w for w, _ in theme_counts.most_common(8)]  # a few extra for LLM selection
    polarity = _label_polarity(polarity_total)
    repeats = _repeating_phrases(responses)

    return {
        "themes": themes,
        "theme_counts": dict(theme_counts.most_common(30)),
        "polarity": polarity,
        "repeating_phrases": repeats,
        "polarity_score": polarity_total,
    }


def _build_theme_candidates(signals: Dict[str, Any]) -> List[Tuple[str, int]]:
    """Return sorted (token, count) candidates."""
    raw = signals.get("theme_counts") or {}
    items = [(k, int(v)) for k, v in raw.items() if k and isinstance(v, (int, float, str))]
    # coerce string numbers
    cleaned: List[Tuple[str, int]] = []
    for k, v in items:
        try:
            cleaned.append((k, int(float(v))))
        except Exception:
            continue
    cleaned.sort(key=lambda x: x[1], reverse=True)
    return cleaned[:20]


# -----------------------------
# Gemini API (LLM report)
# -----------------------------

#define system prompt for Gemini
SYSTEM_PROMPT = """You are a supportive self-discovery coach writing a WEEKLY reflection report.
The user is NOT an experienced journaler. Keep it warm, specific, and non-judgmental.
Do NOT diagnose or mention therapy. Do NOT mention that you are an AI.

You MUST produce:
1) Up to 5 themes that reflect what the USER wrote about in their RESPONSES.
2) For each theme: a percentage (0–100) based on how frequently it appears relative to the other themes.
   Percentages must sum to 100.
3) For each theme: 2–3 concrete details (names, places, specific items, etc.) pulled from the user's entries.
4) Emotional polarity label: positive / neutral / negative
5) Repeating phrases (e.g., “I feel…”, “I’m worried…”)
6) A short narrative summary similar to:
   “This week, you wrote most about X, Y, Z. You felt most energized when talking about A and B.”

CRITICAL CONSTRAINTS:
- Themes must NOT be copied from the app prompts or from the instructions you are given.
- Do NOT use generic prompt-like labels such as “self-discovery”, “reflection”, “journaling”, “weekly report”, “most common themes”.
- Theme names should be 1–3 words, natural, and specific.
- Details must be short fragments (1–4 words each). No full sentences.
- Never include quotes from the instruction text.

Output format: return VALID JSON ONLY with this schema:
{
  "themes": [
    {"theme": "...", "percent": 0, "details": ["...", "...", "..."]}
  ],
  "polarity": "positive|neutral|negative",
  "repeating_phrases": ["..."],
  "summary": "..."
}

Constraints:
- Keep summary under 80 words.
- Avoid clichés. Avoid excessive cheerleading.
- If entries are sparse, acknowledge lightly and still provide a helpful summary.
"""


def _gemini_weekly_json(entries: List[Dict[str, Any]], signals: Dict[str, Any]) -> Dict[str, Any]:
    """Gemini produces structured JSON for themes + percents + details."""
    if genai is None or types is None:
        raise RuntimeError("google-genai is not installed or failed to import")

    model = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

    # Candidate theme tokens (response-derived only)
    candidates = _build_theme_candidates(signals)
    cand_str = ", ".join([f"{t}:{c}" for t, c in candidates]) if candidates else "(none)"

    # Keep token usage predictable: snippets of responses only
    response_snippets = []
    for i, e in enumerate(entries[:14], start=1):
        response = (e.get("response") or "").strip()
        if not response:
            continue
        if len(response) > 320:
            response = response[:320].rstrip() + "…"
        response_snippets.append(f"{i}. {response}")

    user_payload = (
        "Signals (computed from responses only):\n"
        f"- candidate_theme_tokens_with_counts: {cand_str}\n"
        f"- polarity: {signals.get('polarity', 'neutral')} (score={signals.get('polarity_score', 0)})\n"
        f"- repeating_phrases: {signals.get('repeating_phrases', [])}\n\n"
        "User responses (snippets):\n"
        + ("\n".join(response_snippets) if response_snippets else "(No usable responses provided)")
    )

    client = genai.Client()
    resp = client.models.generate_content(
        model=model,
        contents=user_payload,
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT,
            temperature=0.3,
            max_output_tokens=320,
            response_mime_type="application/json",
        ),
    )

    text = (resp.text or "").strip()
    if not text:
        raise RuntimeError("Gemini returned empty response")
    try:
        return json.loads(text)
    except Exception as e:
        raise RuntimeError(f"Gemini did not return valid JSON: {e}")

def _clamp_percent(p: Any) -> int:
    try:
        n = int(round(float(p)))
    except Exception:
        return 0
    return max(0, min(100, n))


def _normalize_theme_json(obj: Dict[str, Any]) -> Dict[str, Any]:
    """Best-effort cleanup/validation so the frontend doesn't explode."""
    themes = obj.get("themes") if isinstance(obj, dict) else None
    if not isinstance(themes, list):
        themes = []

    cleaned = []
    for t in themes[:5]:
        if not isinstance(t, dict):
            continue
        name = (t.get("theme") or "").strip()
        if not name:
            continue
        percent = _clamp_percent(t.get("percent"))
        details = t.get("details")
        if not isinstance(details, list):
            details = []
        details = [str(d).strip() for d in details if str(d).strip()][:3]
        cleaned.append({"theme": name, "percent": percent, "details": details})

    # Fix percent sum if needed
    total = sum(t["percent"] for t in cleaned)
    if cleaned and total != 100:
        # scale then fix rounding
        if total <= 0:
            # equal split
            base = 100 // len(cleaned)
            for i in range(len(cleaned)):
                cleaned[i]["percent"] = base
            cleaned[0]["percent"] += 100 - sum(t["percent"] for t in cleaned)
        else:
            scaled = []
            for t in cleaned:
                scaled.append(int(round(t["percent"] * 100 / total)))
            diff = 100 - sum(scaled)
            if scaled:
                scaled[0] += diff
            for i, v in enumerate(scaled):
                cleaned[i]["percent"] = _clamp_percent(v)

    polarity = obj.get("polarity") if isinstance(obj, dict) else None
    if polarity not in ("positive", "neutral", "negative"):
        polarity = "neutral"

    repeating_phrases = obj.get("repeating_phrases") if isinstance(obj, dict) else None
    if not isinstance(repeating_phrases, list):
        repeating_phrases = []
    repeating_phrases = [str(x).strip() for x in repeating_phrases if str(x).strip()][:3]

    summary = (obj.get("summary") if isinstance(obj, dict) else "") or ""
    summary = str(summary).strip()

    return {
        "themes": cleaned,
        "polarity": polarity,
        "repeating_phrases": repeating_phrases,
        "summary": summary,
    }


def _extract_theme_details_fallback(theme: str, entries: List[Dict[str, Any]]) -> List[str]:
    """Heuristic detail extractor from user responses.

    This is ONLY used when Gemini fails to return usable details.
    We look for responses mentioning the theme, then surface 2–3
    concrete fragments (proper nouns / specific items) from those responses.
    """
    theme_l = (theme or "").strip().lower()
    if not theme_l:
        return []

    matched_texts: List[str] = []
    for e in entries:
        resp = (e.get("response") or "").strip()
        if not resp:
            continue
        if theme_l in resp.lower():
            matched_texts.append(resp)

    # If nothing explicitly mentions the theme word, use all responses.
    if not matched_texts:
        matched_texts = [(e.get("response") or "").strip() for e in entries if (e.get("response") or "").strip()]

    # 1) Pull proper-noun phrases like "Frank Ocean", "New York".
    proper_counts = Counter()
    proper_pat = re.compile(r"\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+){0,2})\b")
    for t in matched_texts:
        for m in proper_pat.findall(t):
            frag = m.strip()
            if not frag:
                continue
            # Filter very generic capitalized words that often appear at sentence start
            if frag.lower() in {"i", "im", "i'm", "today", "this", "that", "week"}:
                continue
            if theme_l in frag.lower():
                continue
            proper_counts[frag] += 1

    # 2) Pull frequent non-stopword tokens from matched responses.
    token_counts = Counter()
    for t in matched_texts:
        for w in _tokenize(t):
            if w == theme_l:
                continue
            token_counts[w] += 1

    details: List[str] = []

    # Prefer proper nouns first (more "concrete")
    for frag, _ in proper_counts.most_common(6):
        if frag not in details:
            details.append(frag)
        if len(details) >= 3:
            return details

    # Then fill with top tokens (title-cased for display)
    for w, _ in token_counts.most_common(10):
        disp = w
        if disp and disp not in details:
            details.append(disp)
        if len(details) >= 3:
            break

    # Keep it to 2–3 if we can
    return details[:3]


# -----------------------------
# 3) Public function used by routes/insights.py
# -----------------------------

def generate_weekly_insights(entries: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Returns a dict suitable for your /insights/weekly endpoint.

    Always returns computed signals.
    Tries Gemini for the human report; falls back to a simple template if Gemini fails.
    """
    signals = _extract_signals(entries)

    # -----------------
    # Fallback (no Gemini): compute percentages from response-token counts
    # -----------------
    candidates = _build_theme_candidates(signals)
    top = candidates[:5]
    total = sum(c for _, c in top) or 0

    fallback_theme_objs = []
    if top and total > 0:
        # initial rounding
        percents = [int(round(c * 100 / total)) for _, c in top]
        diff = 100 - sum(percents)
        percents[0] += diff
        for (tok, _c), p in zip(top, percents):
            fallback_theme_objs.append({"theme": tok, "percent": _clamp_percent(p), "details": []})

    repeats = signals["repeating_phrases"]
    theme_names = [t[0] for t in top] if top else signals.get("themes", [])
    theme_str = ", ".join(theme_names[:3]) if theme_names else "a few recurring topics"
    repeats_str = ", ".join(repeats) if repeats else "None"
    fallback_summary = (
        f"This week, you wrote most about {theme_str}. Overall tone: {signals['polarity']}."
    ).strip()

    # Try Gemini structured JSON
    used_gemini = False
    gemini_error = None
    gemini_obj: Dict[str, Any] | None = None

    try:
        if os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY"):
            gemini_raw = _gemini_weekly_json(entries, signals)
            gemini_obj = _normalize_theme_json(gemini_raw)
            used_gemini = True
    except Exception as e:
        gemini_error = str(e)
        gemini_obj = None

    final_obj = gemini_obj or {
        "themes": fallback_theme_objs,
        "polarity": signals["polarity"],
        "repeating_phrases": repeats,
        "summary": fallback_summary,
    }

    # Ensure bubble details are NEVER empty (the frontend should not show defaults).
    # If Gemini didn't provide details, extract 2–3 concrete fragments from the entries.
    fixed_themes: List[Dict[str, Any]] = []
    for t in final_obj.get("themes", [])[:5]:
        if not isinstance(t, dict):
            continue
        name = str(t.get("theme") or "").strip()
        if not name:
            continue
        details = t.get("details")
        if not isinstance(details, list):
            details = []
        details = [str(d).strip() for d in details if str(d).strip()]
        if len(details) < 2:
            details = _extract_theme_details_fallback(name, entries)
        fixed_themes.append(
            {
                "theme": name,
                "percent": _clamp_percent(t.get("percent")),
                "details": details[:3],
            }
        )
    final_obj["themes"] = fixed_themes

    # A legacy-friendly text report (optional, still useful for demos/debug)
    theme_line = ", ".join([t["theme"] for t in final_obj.get("themes", [])]) or "None"
    report_text = (
        f"Themes: {theme_line}\n"
        f"Polarity: {final_obj.get('polarity', 'neutral')}\n"
        f"Repeating phrases: {repeats_str}\n"
        f"Summary: {final_obj.get('summary', fallback_summary)}"
    ).strip()

    return {
        # New structured themes for bubble sizing + details
        "themes": final_obj.get("themes", []),
        "summary": final_obj.get("summary", ""),

        # Keep these for existing UI pieces
        "polarity": final_obj.get("polarity", signals["polarity"]),
        "repeating_phrases": final_obj.get("repeating_phrases", signals["repeating_phrases"]),

        # Legacy/plain themes (backwards compatibility)
        "themes_plain": signals.get("themes", []),

        # Debug/demo
        "report": report_text,
        "used_gemini": used_gemini,
        "gemini_error": gemini_error,
    }
