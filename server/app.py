from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List

from logic.promptPicker import get_prompt_for_today
from logic.insightEngine import generate_weekly_insights

# create FastAPI app
app = FastAPI(title="Self-Discovery Backend")

# allow React dev server (Vite default is 5173)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -----------------------
# Models 
# -----------------------
class Entry(BaseModel):
    prompt: str = Field(..., min_length=1, max_length=300)
    response: str = Field(..., min_length=1, max_length=2000)
    timestamp: int  # ms since epoch

class WeeklyInsightRequest(BaseModel):
    entries: List[Entry]

# -----------------------
# Endpoints
# -----------------------
# test endpoint
@app.get("/health")
def health():
    return {"status": "ok"}

# Endpoint to get today's prompt
@app.get("/prompt/today")
def prompt_today():
    """
    Returns:
      {
        "prompt": {
          "id": "...",
          "category": "...",
          "prompt": "..."
        }
      }
    """
    return {"prompt": get_prompt_for_today()}

# Endpoint to get weekly insights
@app.post("/insights/weekly")
def insights_weekly(payload: WeeklyInsightRequest):
    """
    Frontend loads entries from LocalStorage and sends them here.
    Backend returns computed signals + Gemini-generated report (or fallback).
    """
    entries_as_dicts = [e.model_dump() for e in payload.entries]
    return generate_weekly_insights(entries_as_dicts)
