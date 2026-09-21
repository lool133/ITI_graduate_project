import { useEffect } from "react";

export default function StatusBar({ health, onCheck }) {
  useEffect(() => {
    onCheck();
    const id = setInterval(onCheck, 30_000);
    return () => clearInterval(id);
  }, [onCheck]);

  if (!health) {
    return (
      <div className="status-bar status-checking">
        <span className="dot dot-yellow" />
        Connecting to backend…
      </div>
    );
  }

  if (health.status === "unreachable") {
    return (
      <div className="status-bar status-error">
        <span className="dot dot-red" />
        Backend unreachable — is <code>python run.py</code> running?
      </div>
    );
  }

  return (
    <div className="status-bar status-ok">
      <span className="dot dot-green" />
      <span>
        API <strong>online</strong>
        {" · "}
        Vector store: <strong>{health.index_ready ? `✓ (${health.index_size?.toLocaleString()} chunks)` : "✗ not loaded"}</strong>
        {" · "}
        Gemini: <strong>{health.ollama_ready ? "✓" : "✗ offline"}</strong>
        {" · "}
        Model: <strong>{health.model}</strong>
      </span>
    </div>
  );
}
