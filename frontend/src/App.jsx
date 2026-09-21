import { useEffect, useRef } from "react";
import { useChat } from "./hooks/useChat";
import MessageBubble from "./components/MessageBubble";
import ChatInput from "./components/ChatInput";
import StatusBar from "./components/StatusBar";
import "./App.css";

export default function App() {
  const { messages, loading, health, sendMessage, checkHealth, clearChat } = useChat();
  const bottomRef = useRef(null);

  // Scroll to bottom on new messages
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  return (
    <div className="app">
      {/* ── Header ── */}
      <header className="header">
        <div className="header-left">
          <span className="header-icon" aria-hidden="true">🔒</span>
          <div>
            <h1 className="header-title">Privacy Compliance Assistant</h1>
            <p className="header-subtitle">GDPR · EDPB Guidelines · Egypt PDPL 151/2020</p>
          </div>
        </div>
        <button
          className="clear-btn"
          onClick={clearChat}
          title="Clear conversation"
          aria-label="Clear conversation"
        >
          Clear chat
        </button>
      </header>

      {/* ── Status bar ── */}
      <StatusBar health={health} onCheck={checkHealth} />

      {/* ── Message list ── */}
      <main className="messages-pane" aria-live="polite" aria-label="Conversation">
        {messages.map((msg) => (
          <MessageBubble key={msg.id} msg={msg} />
        ))}

        {loading && (
          <div className="bubble-row bubble-row--assistant">
            <div className="avatar avatar--bot">AI</div>
            <div className="bubble bubble--assistant bubble--thinking">
              <span className="dot-pulse" aria-label="Thinking…" />
              <span className="dot-pulse" style={{ animationDelay: "0.15s" }} />
              <span className="dot-pulse" style={{ animationDelay: "0.3s" }} />
            </div>
          </div>
        )}

        <div ref={bottomRef} />
      </main>

      {/* ── Input ── */}
      <footer className="input-footer">
        <ChatInput onSend={sendMessage} loading={loading} />
      </footer>
    </div>
  );
}
