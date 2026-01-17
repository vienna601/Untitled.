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
from typing import Any, Dict, List

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
    "today", "week", "really", "just", "like", "got", "get"
}

# Very lightweight lexicon-based sentiment analysis
# (for demo purposes; replace with a proper library for production)
POS_WORDS = {
    "calm", "good", "great", "proud", "excited", "happy", "relieved", "grateful",
    "energized", "hopeful", "confident", "peaceful", "motivated"
}
NEG_WORDS = {
    "tired", "anxious", "worried", "sad", "angry", "overwhelmed", "stressed",
    "upset", "frustrated", "guilty", "lonely", "burnt", "burned"
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
    texts = [f"{e.get('prompt','')} {e.get('response','')}".strip() for e in entries]
    responses = [(e.get("response") or "").strip() for e in entries]

    tokens: List[str] = []
    polarity_total = 0

    for t in texts:
        tokens.extend(_tokenize(t))
        polarity_total += _polarity_score(t)

    themes = [w for w, _ in Counter(tokens).most_common(5)]
    polarity = _label_polarity(polarity_total)
    repeats = _repeating_phrases(responses)

    return {
        "themes": themes,
        "polarity": polarity,
        "repeating_phrases": repeats,
        "polarity_score": polarity_total,
    }


# -----------------------------
# Gemini API (LLM report)
# -----------------------------

#define system prompt for Gemini
SYSTEM_PROMPT = """You are a supportive self-discovery coach writing a WEEKLY reflection report.
The user is NOT an experienced journaler. Keep it warm, specific, and non-judgmental.
Do NOT diagnose or mention therapy. Do NOT mention that you are an AI.

You MUST produce a weekly summary that includes:
1) Most common themes (keywords)
2) Emotional polarity label: positive / neutral / negative
3) Repeating phrases (e.g., “I feel…”, “I’m worried…”)
4) A short narrative summary similar to:
   “This week, you wrote most about X, Y, Z. You felt most energized when talking about A and B.”

Output format (exact headings):
Themes: <comma-separated keywords, 3–5 items>
Polarity: <positive|neutral|negative>
Repeating phrases: <comma-separated phrases, 0–3 items or 'None'>
Summary: <2–4 sentences, concise, human, encouraging>

Constraints:
- Total output under 120 words.
- Avoid clichés. Avoid excessive cheerleading.
- If entries are sparse, acknowledge lightly and still provide a helpful summary.
"""

def _gemini_weekly_report(entries: List[Dict[str, Any]], signals: Dict[str, Any]) -> str:
    """
    Uses Gemini to generate the final report text.
    Requires:
      - google-genai installed
      - GEMINI_API_KEY set (or GOOGLE_API_KEY)
    """
    if genai is None or types is None:
        raise RuntimeError("google-genai is not installed or failed to import")

    #get model from env or use default
    model = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

    # Keep prompt small but concrete by including signals and short entry snippets.
    # (We don't need full long journal text to get a good report.)
    entry_snippets = []
    for i, e in enumerate(entries[:14], start=1):  # cap to keep token usage predictable
        prompt = (e.get("prompt") or "").strip()
        response = (e.get("response") or "").strip()
        if not response:
            continue
        # Truncate response snippet
        if len(response) > 280:
            response = response[:280].rstrip() + "…"
        entry_snippets.append(f"{i}. Prompt: {prompt}\n   Response: {response}")

    user_payload = (
        "Weekly signals (computed):\n"
        f"- themes: {signals.get('themes', [])}\n"
        f"- polarity: {signals.get('polarity', 'neutral')} (score={signals.get('polarity_score', 0)})\n"
        f"- repeating_phrases: {signals.get('repeating_phrases', [])}\n\n"
        "Entries (snippets):\n"
        + ("\n".join(entry_snippets) if entry_snippets else "(No usable entries provided)")
    )
    # reads GEMINI_API_KEY / GOOGLE_API_KEY from env
    client = genai.Client() 
    #generate content
    resp = client.models.generate_content(
        model=model,
        contents=user_payload,
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT,
            temperature=0.4,
            max_output_tokens=220,
        ),
    )
    return (resp.text or "").strip()


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

    # Fallback report (if Gemini not configured)
    themes = signals["themes"]
    theme_str = ", ".join(themes[:3]) if themes else "a few recurring topics"
    repeats = signals["repeating_phrases"]
    repeats_str = ", ".join(repeats) if repeats else "None"

    fallback_report = (
        f"Themes: {', '.join(themes[:5]) if themes else 'None'}\n"
        f"Polarity: {signals['polarity']}\n"
        f"Repeating phrases: {repeats_str}\n"
        f"Summary: This week, you wrote most about {theme_str}. "
        f"Overall tone: {signals['polarity']}. "
        f"{'Common phrasing included ' + repeats_str + '.' if repeats else ''}"
    ).strip()

    # Try Gemini
    report_text = fallback_report
    used_gemini = False
    gemini_error = None

    try:
        # Only attempt if an API key exists (common hackathon gotcha)
        if os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY"):
            report_text = _gemini_weekly_report(entries, signals)
            if report_text:
                used_gemini = True
            else:
                report_text = fallback_report
    except Exception as e:
        gemini_error = str(e)
        report_text = fallback_report

    return {
        "themes": signals["themes"],
        "polarity": signals["polarity"],
        "repeating_phrases": signals["repeating_phrases"],
        "report": report_text,          # Gemini output (or fallback)
        "used_gemini": used_gemini,
        "gemini_error": gemini_error,   # helpful for debugging; you can remove for demo
    }
