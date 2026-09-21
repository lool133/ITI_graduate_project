import { useState, useRef, useEffect } from "react";

const SUGGESTED = [
  "What are the rights of data subjects under GDPR?",
  "What is the lawful basis for processing personal data?",
  "How does Egypt's PDPL 151/2020 define personal data?",
  "What are the GDPR requirements for a Data Protection Impact Assessment?",
  "What are the breach notification obligations under GDPR?",
];

export default function ChatInput({ onSend, loading }) {
  const [text, setText] = useState("");
  const [topK, setTopK] = useState(5);
  const textareaRef = useRef(null);

  // Auto-resize textarea
  useEffect(() => {
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = Math.min(el.scrollHeight, 160) + "px";
  }, [text]);

  const submit = () => {
    const q = text.trim();
    if (!q || loading) return;
    onSend(q, topK);
    setText("");
  };

  const handleKey = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      submit();
    }
  };

  return (
    <div className="chat-input-wrapper">
      {/* Suggested questions */}
      <div className="suggestions">
        {SUGGESTED.map((s) => (
          <button
            key={s}
            className="suggestion-chip"
            onClick={() => onSend(s, topK)}
            disabled={loading}
          >
            {s}
          </button>
        ))}
      </div>

      <div className="input-row">
        <textarea
          ref={textareaRef}
          className="chat-textarea"
          rows={1}
          placeholder="Ask about GDPR, EDPB guidelines, or Egypt PDPL…"
          value={text}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={handleKey}
          disabled={loading}
          aria-label="Question input"
        />

        <div className="input-controls">
          <label className="topk-label" title="Number of retrieved source chunks">
            Top-K
            <input
              type="number"
              className="topk-input"
              min={1}
              max={20}
              value={topK}
              onChange={(e) => setTopK(Number(e.target.value))}
              disabled={loading}
              aria-label="Top-K retrieval count"
            />
          </label>

          <button
            className="send-btn"
            onClick={submit}
            disabled={!text.trim() || loading}
            aria-label="Send message"
          >
            {loading ? (
              <span className="spinner" aria-hidden="true" />
            ) : (
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"
                   strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                <line x1="22" y1="2" x2="11" y2="13" />
                <polygon points="22 2 15 22 11 13 2 9 22 2" />
              </svg>
            )}
          </button>
        </div>
      </div>

      <p className="input-hint">
        Enter to send · Shift+Enter for new line
      </p>
    </div>
  );
}
