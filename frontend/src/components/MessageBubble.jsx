import { useState } from "react";

/** Very lightweight markdown renderer — bold, code, newlines. */
function renderText(text) {
  return text
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
    .replace(/`([^`]+)`/g, "<code>$1</code>")
    .replace(/\n/g, "<br />");
}

function SourceCard({ source, index }) {
  const [open, setOpen] = useState(false);
  return (
    <div className="source-card">
      <button className="source-toggle" onClick={() => setOpen((o) => !o)}>
        <span className="source-index">[{index}]</span>
        <span className="source-file">{source.source}</span>
        {source.page != null && (
          <span className="source-page">p. {source.page}</span>
        )}
        <span className="source-dist">dist {source.distance.toFixed(3)}</span>
        <span className="chevron">{open ? "▲" : "▼"}</span>
      </button>
      {open && (
        <div className="source-snippet">
          {source.text}
          {source.text.length >= 400 ? "…" : ""}
        </div>
      )}
    </div>
  );
}

export default function MessageBubble({ msg }) {
  const isUser = msg.role === "user";

  return (
    <div className={`bubble-row ${isUser ? "bubble-row--user" : "bubble-row--assistant"}`}>
      <div className={`avatar ${isUser ? "avatar--user" : "avatar--bot"}`}>
        {isUser ? "You" : "AI"}
      </div>

      <div className="bubble-content">
        <div
          className={`bubble ${isUser ? "bubble--user" : msg.isError ? "bubble--error" : "bubble--assistant"}`}
          dangerouslySetInnerHTML={{ __html: renderText(msg.text) }}
        />

        {!isUser && msg.sources?.length > 0 && (
          <div className="sources-section">
            <p className="sources-label">📚 Sources ({msg.sources.length})</p>
            {msg.sources.map((s, i) => (
              <SourceCard key={i} source={s} index={i + 1} />
            ))}
          </div>
        )}

        {!isUser && msg.latency != null && (
          <div className="bubble-meta">
            {msg.model && <span>{msg.model}</span>}
            <span>{msg.latency.toLocaleString()} ms</span>
          </div>
        )}
      </div>
    </div>
  );
}
