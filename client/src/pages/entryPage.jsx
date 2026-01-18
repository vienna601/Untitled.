import { useState, useEffect } from 'react';
import '../styles/entryPage.css';
import soundGif from '../assets/sound.gif';
import enterIcon from '../assets/enter.png';

const API_BASE = 'http://localhost:8000';
const STORAGE_KEY = 'journal_entries';

const saveEntry = (entry) => {
  const entries = JSON.parse(localStorage.getItem(STORAGE_KEY) || '[]');
  entries.push(entry);
  localStorage.setItem(STORAGE_KEY, JSON.stringify(entries));
};

export default function EntryPage({ onNavigate }) {
  const [prompt, setPrompt] = useState(null);
  const [response, setResponse] = useState('');
  const [isRecording, setIsRecording] = useState(false);
  const [mediaRecorder, setMediaRecorder] = useState(null);
  const [isTranscribing, setIsTranscribing] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState(false);

  useEffect(() => {
    loadPrompt();
  }, []);

  const loadPrompt = async () => {
    try {
      const res = await fetch(`${API_BASE}/prompt/today`);
      if (!res.ok) throw new Error('Failed to fetch');
      const data = await res.json();
      setPrompt(data.prompt);
      setError('');
    } catch (e) {
      console.error('Error loading prompt:', e);
      setError('Cannot connect to backend. Please make sure the server is running on port 8000.');
    }
  };

  const toggleRecording = async () => {
    if (isRecording) {
      stopRecording();
    } else {
      startRecording();
    }
  };

  const startRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const recorder = new MediaRecorder(stream);
      const chunks = [];

      recorder.ondataavailable = (e) => chunks.push(e.data);
      
      recorder.onstop = async () => {
        const blob = new Blob(chunks, { type: 'audio/webm' });
        stream.getTracks().forEach(track => track.stop());
        
        setIsTranscribing(true);
        try {
          const formData = new FormData();
          formData.append('file', blob, 'audio.webm');
          
          const res = await fetch(`${API_BASE}/stt/transcribe`, {
            method: 'POST',
            body: formData,
          });
          
          if (!res.ok) throw new Error('Transcription failed');
          
          const data = await res.json();
          setResponse(prev => (prev ? prev + ' ' : '') + data.text);
          setError('');
        } catch (e) {
          console.error('Transcription error:', e);
          setError('Failed to transcribe. Please check if the backend is running.');
        } finally {
          setIsTranscribing(false);
        }
      };

      recorder.start();
      setMediaRecorder(recorder);
      setIsRecording(true);
      setError('');
    } catch (e) {
      console.error('Recording error:', e);
      setError('Microphone access denied. Please allow microphone access.');
    }
  };

  const stopRecording = () => {
    if (mediaRecorder && isRecording) {
      mediaRecorder.stop();
      setIsRecording(false);
      setMediaRecorder(null);
    }
  };

  const handleSubmit = () => {
    if (response.trim().length < 10) {
      setError('Please write at least one sentence (10+ characters).');
      return;
    }

    try {
      const entry = {
        prompt: prompt.prompt,
        response: response.trim(),
        timestamp: Date.now(),
      };
      
      saveEntry(entry);
      setSuccess(true);
      
      setTimeout(() => {
        setResponse('');
        setSuccess(false);
        setError('');
        loadPrompt();
      }, 2000);
    } catch (e) {
      setError('Failed to save entry.');
    }
  };

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  return (
    <div className="entry-page">
      <div className="entry-page__header">
        <h1 className="entry-page__title">Untitled.</h1>
      </div>

      <div className="entry-page__content">
        {prompt ? (
          <>
            <button
              onClick={toggleRecording}
              disabled={isTranscribing}
              className="entry-page__voice-bubble"
            >
              <img 
                src={soundGif} 
                alt="Recording" 
                className={`entry-page__voice-animation ${isRecording ? 'recording' : ''}`}
              />
              <div className={`entry-page__voice-placeholder ${isRecording ? 'recording' : ''}`}>
                {isTranscribing ? 'Transcribing...' : 'Click to record'}
              </div>
            </button>

            <h2 className="entry-page__prompt">{prompt.prompt}</h2>

            <div className="entry-page__input-container">
              <input
                type="text"
                value={response}
                onChange={(e) => setResponse(e.target.value)}
                onKeyPress={handleKeyPress}
                placeholder="Voice your thoughts..."
                disabled={isRecording || isTranscribing}
                className="entry-page__input"
              />
              <button
                onClick={handleSubmit}
                disabled={isRecording || isTranscribing || response.trim().length < 10}
                className="entry-page__enter-button"
              >
                <img src={enterIcon} alt="Submit" className="entry-page__enter-icon" />
              </button>
            </div>

            {error && <div className="entry-page__error">{error}</div>}
            {success && <div className="entry-page__success">Entry saved successfully!</div>}
          </>
        ) : (
          <div className="entry-page__loading">
            {error || 'Loading prompt...'}
          </div>
        )}
      </div>

      <div className="entry-page__footer">
        <button onClick={() => onNavigate('report')} className="entry-page__view-report">
          View Weekly Report
        </button>
      </div>
    </div>
  );
}