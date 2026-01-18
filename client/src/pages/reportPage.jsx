import { useState, useEffect } from 'react';
import '../styles/reportPage.css';

const API_BASE = 'http://localhost:8000';
const STORAGE_KEY = 'journal_entries';

const getWeekEntries = () => {
  const entries = JSON.parse(localStorage.getItem(STORAGE_KEY) || '[]');
  const weekAgo = Date.now() - (7 * 24 * 60 * 60 * 1000);
  return entries.filter(e => e.timestamp >= weekAgo);
};

export default function ReportPage({ onNavigate }) {
  const [insights, setInsights] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');
  const weekEntries = getWeekEntries();

  useEffect(() => {
    if (weekEntries.length > 0) {
      loadInsights();
    }
  }, []);

  const loadInsights = async () => {
    setIsLoading(true);
    setError('');
    
    try {
      const res = await fetch(`${API_BASE}/insights/weekly`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ entries: weekEntries }),
      });
      
      if (!res.ok) throw new Error('Failed to fetch insights');
      
      const data = await res.json();
      setInsights(data);
    } catch (e) {
      console.error('Error loading insights:', e);
      setError('Cannot connect to backend. Please make sure the server is running.');
    } finally {
      setIsLoading(false);
    }
  };

  const getBubbleClass = (index) => {
    if (index === 0) return 'report-page__bubble--primary';
    if (index === 1) return 'report-page__bubble--secondary-1';
    if (index === 2) return 'report-page__bubble--secondary-2';
    if (index === 3) return 'report-page__bubble--secondary-3';
    if (index === 4) return 'report-page__bubble--secondary-4';
    return '';
  };

  const getBubbleLabel = (index, repeatingPhrases) => {
    if (index === 0) return 'Primary Theme';
    if (index === 1 && repeatingPhrases && repeatingPhrases.length > 0) {
      return repeatingPhrases[0];
    }
    if (index === 2 && repeatingPhrases && repeatingPhrases.length > 1) {
      return repeatingPhrases[1];
    }
    return 'Recurring Theme';
  };

  return (
    <div className="report-page">
      <div className="report-page__header">
        <h1 className="report-page__title">Untitled.</h1>
      </div>

      {weekEntries.length === 0 ? (
        <div className="report-page__no-entries">
          <p className="report-page__no-entries-text">No entries yet this week.</p>
          <button onClick={() => onNavigate('entry')} className="report-page__start-button">
            Start journaling
          </button>
        </div>
      ) : isLoading ? (
        <div className="report-page__loading">
          <p className="report-page__loading-text">Analyzing your reflections...</p>
        </div>
      ) : error ? (
        <div className="report-page__loading">
          <p className="report-page__loading-text" style={{ color: '#dc2626' }}>{error}</p>
          <button onClick={loadInsights} className="report-page__start-button">
            Retry
          </button>
        </div>
      ) : insights ? (
        <>
          <h2 className="report-page__report-title">Weekly Report</h2>

          <div className="report-page__bubbles-container">
            {insights.themes && insights.themes.slice(0, 5).map((theme, index) => (
              <div
                key={index}
                className={`report-page__bubble ${getBubbleClass(index)}`}
              >
                <p className="report-page__bubble-topic">{theme}</p>
                <p className="report-page__bubble-details">
                  {getBubbleLabel(index, insights.repeating_phrases)}
                </p>
              </div>
            ))}
          </div>
        </>
      ) : null}

      <div className="report-page__footer">
        <button onClick={() => onNavigate('entry')} className="report-page__back-button">
          Back
        </button>
      </div>
    </div>
  );
}