import { useEffect, useRef, useState } from "react";
import { transcribeAudioBlob } from "../services/stt";
import { fetchTodayPrompt } from "../services/api";

export default function Entry() {
  const [promptText, setPromptText] = useState("");
  const [isLoadingPrompt, setIsLoadingPrompt] = useState(true);
  const [response, setResponse] = useState("");
  const [isRecording, setIsRecording] = useState(false);
  const [isTranscribing, setIsTranscribing] = useState(false);
  const [error, setError] = useState("");

  const mediaRecorderRef = useRef(null);
  const streamRef = useRef(null);
  const chunksRef = useRef([]);

  // Fetch today’s prompt on mount
  useEffect(() => {
    async function loadPrompt() {
      try {
        const data = await fetchTodayPrompt();
        setPromptText(data.prompt.prompt); // backend shape: { prompt: { id, category, prompt } }
      } catch (err) {
        setError("Failed to load today’s prompt.");
      } finally {
        setIsLoadingPrompt(false);
      }
    }

    loadPrompt();
  }, []);

  // Clean up mic stream if user navigates away
  useEffect(() => {
    return () => {
      try {
        if (
          mediaRecorderRef.current &&
          mediaRecorderRef.current.state !== "inactive"
        ) {
          mediaRecorderRef.current.stop();
        }
      } catch {}
      stopStream();
    };
  }, []);

  function stopStream() {
    if (streamRef.current) {
      streamRef.current.getTracks().forEach((t) => t.stop());
      streamRef.current = null;
    }
  }

  function pickBestMimeType() {
    // Browser support varies. We'll try a few common types.
    const candidates = [
      "audio/webm;codecs=opus",
      "audio/webm",
      "audio/ogg;codecs=opus",
      "audio/ogg",
    ];
    for (const t of candidates) {
      if (window.MediaRecorder && MediaRecorder.isTypeSupported(t)) return t;
    }
    return ""; // let browser choose
  }

  async function startRecording() {
    setError("");

    if (!navigator.mediaDevices?.getUserMedia) {
      setError("Your browser doesn't support audio recording.");
      return;
    }
    if (isRecording || isTranscribing) return;

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      streamRef.current = stream;

      chunksRef.current = [];

      const mimeType = pickBestMimeType();
      const recorder = new MediaRecorder(
        stream,
        mimeType ? { mimeType } : undefined,
      );
      mediaRecorderRef.current = recorder;

      recorder.ondataavailable = (e) => {
        if (e.data && e.data.size > 0) chunksRef.current.push(e.data);
      };

      recorder.onstop = async () => {
        setIsRecording(false);

        // Assemble blob
        const blob = new Blob(chunksRef.current, {
          type: recorder.mimeType || "audio/webm",
        });

        // Stop mic ASAP
        stopStream();

        // If blob is tiny, user likely tapped by accident
        if (blob.size < 1500) return;

        setIsTranscribing(true);
        setError("");

        try {
          const { text } = await transcribeAudioBlob(blob);

          // Auto-fill, but don’t destroy existing text:
          // - If empty: set to transcription
          // - If not empty: append nicely
          if (!text || !text.trim()) {
            setError("No speech detected. Try speaking a bit louder/longer.");
          } else {
            setResponse((prev) => {
              const clean = text.trim();
              if (!prev.trim()) return clean;
              return `${prev.trim()}\n\n${clean}`;
            });
          }
        } catch (err) {
          setError(err?.message || "Transcription failed.");
        } finally {
          setIsTranscribing(false);
        }
      };

      recorder.start();
      setIsRecording(true);
    } catch (err) {
      setError("Microphone permission denied or unavailable.");
      setIsRecording(false);
      stopStream();
    }
  }

  function stopRecording() {
    setError("");
    if (!mediaRecorderRef.current) return;

    try {
      if (mediaRecorderRef.current.state !== "inactive") {
        mediaRecorderRef.current.stop();
      }
    } catch {
      setIsRecording(false);
      stopStream();
    }
  }

  // Hold-to-record handlers (mouse + touch)
  const holdHandlers = {
    onMouseDown: (e) => {
      e.preventDefault();
      startRecording();
    },
    onMouseUp: (e) => {
      e.preventDefault();
      stopRecording();
    },
    onMouseLeave: (e) => {
      // If they drag away while holding, stop
      if (isRecording) stopRecording();
    },
    onTouchStart: (e) => {
      e.preventDefault();
      startRecording();
    },
    onTouchEnd: (e) => {
      e.preventDefault();
      stopRecording();
    },
  };

  function toggleRecording() {
    if (isRecording) stopRecording();
    else startRecording();
  }

  if (isLoadingPrompt) {
    return (
      <div style={{ maxWidth: 720, margin: "40px auto", padding: 16 }}>
        <h2>Loading today’s reflection…</h2>
      </div>
    );
  }

  if (!promptText) {
    return (
      <div
        style={{
          maxWidth: 720,
          margin: "40px auto",
          padding: 16,
          color: "#b00020",
        }}
      >
        Failed to load today’s prompt.
      </div>
    );
  }

  return (
    <div style={{ maxWidth: 720, margin: "40px auto", padding: 16 }}>
      <h2 style={{ marginBottom: 8 }}>Today’s reflection</h2>

      <div
        style={{
          padding: 16,
          border: "1px solid #ddd",
          borderRadius: 12,
          marginBottom: 16,
        }}
      >
        <div style={{ fontSize: 18, lineHeight: 1.4 }}>{promptText}</div>
        <div style={{ marginTop: 8, color: "#666" }}>
          One or two sentences is enough.
        </div>
      </div>

      <label style={{ display: "block", marginBottom: 8, fontWeight: 600 }}>
        Your response
      </label>

      <textarea
        value={response}
        onChange={(e) => setResponse(e.target.value)}
        placeholder="Type here… or record your thoughts."
        rows={8}
        style={{
          width: "100%",
          padding: 12,
          borderRadius: 12,
          border: "1px solid #ddd",
          resize: "vertical",
          fontSize: 16,
          lineHeight: 1.5,
        }}
        disabled={isTranscribing}
      />

      {/* Loading state */}
      {isTranscribing && (
        <div
          style={{
            marginTop: 10,
            padding: 10,
            borderRadius: 10,
            border: "1px solid #ddd",
          }}
        >
          <strong>Transcribing…</strong> Please wait.
        </div>
      )}

      {/* Error message */}
      {!!error && (
        <div style={{ marginTop: 10, color: "#b00020" }}>{error}</div>
      )}

      <div
        style={{
          display: "flex",
          gap: 12,
          marginTop: 16,
          alignItems: "center",
        }}
      >
        {/* Hold-to-record */}
        <button
          type="button"
          {...holdHandlers}
          disabled={isTranscribing}
          style={{
            padding: "12px 14px",
            borderRadius: 12,
            border: "1px solid #ddd",
            cursor: isTranscribing ? "not-allowed" : "pointer",
            minWidth: 160,
            userSelect: "none",
          }}
          aria-pressed={isRecording}
        >
          {isRecording ? "Recording… (release)" : "Hold to record"}
        </button>

        {/* Toggle record */}
        <button
          type="button"
          onClick={toggleRecording}
          disabled={isTranscribing}
          style={{
            padding: "12px 14px",
            borderRadius: 12,
            border: "1px solid #ddd",
            cursor: isTranscribing ? "not-allowed" : "pointer",
            minWidth: 140,
          }}
        >
          {isRecording ? "Stop" : "Record"}
        </button>

        {/* Simple hint */}
        <span style={{ color: "#666" }}>
          {isRecording ? "Speak naturally." : "You can type or record."}
        </span>
      </div>

      {/* Save button placeholder */}
      <div style={{ marginTop: 20 }}>
        <button
          type="button"
          disabled={isTranscribing || !response.trim()}
          style={{
            padding: "12px 16px",
            borderRadius: 12,
            border: "1px solid #ddd",
            cursor:
              isTranscribing || !response.trim() ? "not-allowed" : "pointer",
          }}
          onClick={() => {
            // You’ll replace this with your LocalStorage save logic.
            alert(
              "Saved (placeholder). Hook this to LocalStorage saveEntry().",
            );
          }}
        >
          Save reflection
        </button>
      </div>
    </div>
  );
}
