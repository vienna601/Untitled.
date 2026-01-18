import { useState, useEffect } from "react";
import "../styles/reportPage.css";
import demoEntries from "../data/demoEntries.json";

const API_BASE = "http://localhost:8000";
const STORAGE_KEY = "journal_entries";

const getWeekEntries = () => {
  const entries = JSON.parse(localStorage.getItem(STORAGE_KEY) || "[]");
  const weekAgo = Date.now() - 7 * 24 * 60 * 60 * 1000;
  return entries.filter((e) => e.timestamp >= weekAgo);
};

export default function ReportPage({ onNavigate }) {
  const [insights, setInsights] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState("");
  const weekEntries = getWeekEntries();
  //change to demo data
  //const weekEntries = demoEntries;

  useEffect(() => {
    if (weekEntries.length > 0) {
      loadInsights();
    }
  }, []);

  const loadInsights = async () => {
    setIsLoading(true);
    setError("");

    try {
      const res = await fetch(`${API_BASE}/insights/weekly`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ entries: weekEntries }),
      });

      if (!res.ok) throw new Error("Failed to fetch insights");

      const data = await res.json();
      setInsights(data);
    } catch (e) {
      console.error("Error loading insights:", e);
      setError(
        "Cannot connect to backend. Please make sure the server is running.",
      );
    } finally {
      setIsLoading(false);
    }
  };

  const getBubbleClass = (index) => {
    if (index === 0) return "report-page__bubble--primary";
    if (index === 1) return "report-page__bubble--secondary-1";
    if (index === 2) return "report-page__bubble--secondary-2";
    if (index === 3) return "report-page__bubble--secondary-3";
    if (index === 4) return "report-page__bubble--secondary-4";
    return "";
  };

  // Bubble details come from Gemini-extracted details per theme.
  // We intentionally avoid UI fallbacks like "Primary Theme" / "Recurring Theme".

  const getBubbleSize = (percent, index, maxPercent) => {
    // Primary bubble is larger, others are slightly smaller.
    // We scale by (percent / maxPercent) so the biggest theme is biggest bubble.
    const base = index === 0 ? 360 : 280;
    const minScale = 0.65;
    const maxScale = 1.0;
    const ratio = maxPercent > 0 ? percent / maxPercent : 1;
    const scale = Math.max(minScale, Math.min(maxScale, ratio));
    const size = Math.round(base * scale);
    return { width: `${size}px`, height: `${size}px` };
  };

  const overallPolarity = insights?.polarity || "neutral";

  return (
    <div className={`report-page report-page--${overallPolarity}`}>
      <div className="report-page__header">
        <h1 className="report-page__title">Untitled.</h1>
      </div>

      {weekEntries.length === 0 ? (
        <div className="report-page__no-entries">
          <p className="report-page__no-entries-text">
            No entries yet this week.
          </p>
          <button
            onClick={() => onNavigate("entry")}
            className="report-page__start-button"
          >
            Start journaling
          </button>
        </div>
      ) : isLoading ? (
        <div className="report-page__loading">
          <p className="report-page__loading-text">
            Analyzing your reflections...
          </p>
        </div>
      ) : error ? (
        <div className="report-page__loading">
          <p className="report-page__loading-text" style={{ color: "#dc2626" }}>
            {error}
          </p>
          <button onClick={loadInsights} className="report-page__start-button">
            Retry
          </button>
        </div>
      ) : insights ? (
        <>
          <h2 className="report-page__report-title">Weekly Report</h2>

          <div className="report-page__bubbles-container">
            {(() => {
              const themes = (insights.themes || []).slice(0, 5);
              const maxPercent = themes.reduce(
                (m, t) => Math.max(m, Number(t.percent || 0)),
                0,
              );
              return themes.map((themeObj, index) => (
                <div
                  key={index}
                  className={`report-page__bubble ${getBubbleClass(index)}`}
                  style={getBubbleSize(
                    Number(themeObj.percent || 0),
                    index,
                    maxPercent,
                  )}
                >
                  <p className="report-page__bubble-topic">{themeObj.theme}</p>
                  <p className="report-page__bubble-details">
                    {themeObj.details && themeObj.details.length > 0
                      ? themeObj.details.join(", ")
                      : ""}
                  </p>
                </div>
              ));
            })()}
          </div>
        </>
      ) : null}

      <div className="report-page__footer">
        <button
          onClick={() => onNavigate("entry")}
          className="report-page__back-button"
        >
          Back
        </button>
      </div>
    </div>
  );
}
