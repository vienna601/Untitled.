import os
from io import BytesIO
from elevenlabs.client import ElevenLabs

def transcribe_with_elevenlabs(
    audio_bytes: bytes,
    *,
    filename: str = "audio.webm",
    language_code: str | None = None,  # e.g. "eng" or None for auto-detect
) -> str:
    """
    Calls ElevenLabs Speech-to-Text (Scribe v2) and returns plain text.
    """
    api_key = os.getenv("ELEVENLABS_API_KEY")
    if not api_key:
        raise RuntimeError("Missing ELEVENLABS_API_KEY environment variable")

    client = ElevenLabs(api_key=api_key)

    audio_file = BytesIO(audio_bytes)
    audio_file.name = filename  # some libs use name for file type hints

    transcription = client.speech_to_text.convert(
        file=audio_file,
        model_id="scribe_v2",
        language_code=language_code,     # None = auto-detect :contentReference[oaicite:2]{index=2}
        diarize=False,                   # keep simple for hackathon
        tag_audio_events=False           # keep simple
    )

    # ElevenLabs returns a structured object; "text" is the main transcription string.
    # (SDK may return dict-like or object; handle both)
    if isinstance(transcription, dict):
        return (transcription.get("text") or "").strip()

    return (getattr(transcription, "text", "") or "").strip()
