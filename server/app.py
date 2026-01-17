from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List
from logic.speechToText import transcribe_with_elevenlabs
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

# Endpoint for speech-to-text transcription
@app.post("/stt/transcribe")
async def stt_transcribe(file: UploadFile = File(...), language_code: str | None = None):
    """
    Accepts an audio file upload and returns transcription text.
    Frontend will send multipart/form-data with a Blob.
    """
    # Basic content-type guard (don’t overdo it; browsers vary)
    if not file.content_type or not file.content_type.startswith(("audio/", "video/")):
        raise HTTPException(status_code=400, detail=f"Unsupported content type: {file.content_type}")

    audio_bytes = await file.read()
    if not audio_bytes:
        raise HTTPException(status_code=400, detail="Empty audio file")

    try:
        text = transcribe_with_elevenlabs(
            audio_bytes,
            filename=file.filename or "audio.webm",
            language_code=language_code,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"STT failed: {str(e)}")

    return {"text": text}
