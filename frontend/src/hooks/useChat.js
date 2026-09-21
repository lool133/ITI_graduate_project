import { useState, useCallback } from "react";

const API_BASE = process.env.REACT_APP_API_URL || "http://localhost:8000";

export function useChat() {
  const [messages, setMessages] = useState([
    {
      id: 0,
      role: "assistant",
      text: "Hello! I'm your **Data Protection & Privacy Compliance Assistant**.\n\nAsk me anything about:\n- 🇪🇺 EU GDPR (Regulation 2016/679)\n- 📋 EDPB Guidelines\n- 🇪🇬 Egypt Personal Data Protection Law 151/2020",
      sources: [],
      latency: null,
    },
  ]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [health, setHealth] = useState(null);

  const sendMessage = useCallback(async (question, topK = 5) => {
    if (!question.trim()) return;

    const userMsg = {
      id: Date.now(),
      role: "user",
      text: question,
      sources: [],
      latency: null,
    };
    setMessages((prev) => [...prev, userMsg]);
    setLoading(true);
    setError(null);

    try {
      const res = await fetch(`${API_BASE}/query`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question, top_k: topK }),
      });

      if (!res.ok) {
        const detail = await res.json().catch(() => ({}));
        throw new Error(detail?.detail || `Server error ${res.status}`);
      }

      const data = await res.json();

      setMessages((prev) => [
        ...prev,
        {
          id: Date.now() + 1,
          role: "assistant",
          text: data.answer,
          sources: data.sources || [],
          latency: data.latency_ms,
          model: data.model,
        },
      ]);
    } catch (err) {
      setError(err.message);
      setMessages((prev) => [
        ...prev,
        {
          id: Date.now() + 1,
          role: "assistant",
          text: `⚠️ Error: ${err.message}`,
          sources: [],
          latency: null,
          isError: true,
        },
      ]);
    } finally {
      setLoading(false);
    }
  }, []);

  const checkHealth = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/health`);
      const data = await res.json();
      setHealth(data);
    } catch {
      setHealth({ status: "unreachable" });
    }
  }, []);

  const clearChat = useCallback(() => {
    setMessages((prev) => [prev[0]]); // keep the welcome message
    setError(null);
  }, []);

  return { messages, loading, error, health, sendMessage, checkHealth, clearChat };
}
