import { useState, useRef, useEffect } from "react";
import ApiKeyGate from "./components/ApiKeyGate";
import StockTable from "./components/StockTable";
import { analyzeStock } from "./utils/api";
import type { AgentResponse, ChatMessage, HoldingContext } from "./types";

type Mode = "individual" | "general";

interface ChatEntry {
  role: "user" | "assistant";
  content: string;
  response?: AgentResponse;
}

const QUICK_PROMPTS = [
  "What AI stocks should I buy right now?",
  "Which stocks should I sell or avoid?",
  "Analyze all quantum computing stocks",
  "Best S&P 500 tech stocks this week?",
  "Overall market outlook for AI sector?",
];

export default function App() {
  const [apiKey, setApiKey] = useState<string | null>(null);
  const [sessionId, setSessionId] = useState<string>(() => crypto.randomUUID());
  const [mode, setMode] = useState<Mode>("general");
  const [message, setMessage] = useState("");
  const [chat, setChat] = useState<ChatEntry[]>([]);
  const [loading, setLoading] = useState(false);
  const [holdings, setHoldings] = useState<HoldingContext[]>([]);
  const [newTicker, setNewTicker] = useState("");
  const [newPrice, setNewPrice] = useState("");
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [chat, loading]);

  // Show API key gate until key is provided
  if (!apiKey) {
    return <ApiKeyGate onKeySubmit={setApiKey} />;
  }

  const conversationHistory: ChatMessage[] = chat.map((e) => ({
    role: e.role,
    content: e.content,
  }));

  const send = async (text: string) => {
    if (!text.trim() || loading) return;
    const userEntry: ChatEntry = { role: "user", content: text };
    setChat((prev) => [...prev, userEntry]);
    setMessage("");
    setLoading(true);

    try {
      const res = await analyzeStock(
        {
          message: text,
          mode,
          session_id: sessionId,
          conversation_history: conversationHistory,
          known_holdings: holdings,
        },
        apiKey
      );
      setChat((prev) => [
        ...prev,
        { role: "assistant", content: res.narrative, response: res },
      ]);
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : "Unknown error";
      setChat((prev) => [
        ...prev,
        { role: "assistant", content: `⚠ Error: ${message}` },
      ]);
    } finally {
      setLoading(false);
    }
  };

  const addHolding = () => {
    if (!newTicker.trim() || !newPrice.trim()) return;
    const price = parseFloat(newPrice);
    if (isNaN(price) || price <= 0) return;
    setHoldings((prev) => {
      const filtered = prev.filter(
        (h) => h.ticker !== newTicker.toUpperCase()
      );
      return [...filtered, { ticker: newTicker.toUpperCase(), buy_price: price }];
    });
    setNewTicker("");
    setNewPrice("");
  };

  const removeHolding = (ticker: string) => {
    setHoldings((prev) => prev.filter((h) => h.ticker !== ticker));
  };

  const clearSession = () => {
    setChat([]);
    setSessionId(crypto.randomUUID());
  };

  return (
    <div style={s.root}>
      {/* ── Sidebar ── */}
      <aside style={s.sidebar}>
        <div style={s.sidebarLogo}>⬡ Stock Analyst</div>

        {/* Mode toggle */}
        <div style={s.section}>
          <div style={s.sectionLabel}>MODE</div>
          <div style={s.modeRow}>
            {(["general", "individual"] as Mode[]).map((m) => (
              <button
                key={m}
                onClick={() => setMode(m)}
                style={{
                  ...s.modeBtn,
                  ...(mode === m ? s.modeBtnActive : {}),
                }}
              >
                {m === "general" ? "Market" : "Stock"}
              </button>
            ))}
          </div>
        </div>

        {/* Quick prompts */}
        <div style={s.section}>
          <div style={s.sectionLabel}>QUICK PROMPTS</div>
          {QUICK_PROMPTS.map((p) => (
            <button
              key={p}
              style={s.quickBtn}
              onClick={() => {
                setMode("general");
                send(p);
              }}
            >
              {p}
            </button>
          ))}
        </div>

        {/* Holdings */}
        <div style={s.section}>
          <div style={s.sectionLabel}>MY HOLDINGS</div>
          {holdings.map((h) => (
            <div key={h.ticker} style={s.holdingRow}>
              <span style={s.holdingTicker}>{h.ticker}</span>
              <span style={s.holdingPrice}>${h.buy_price.toFixed(2)}</span>
              <button
                onClick={() => removeHolding(h.ticker)}
                style={s.removeBtn}
                aria-label={`Remove ${h.ticker}`}
              >
                ✕
              </button>
            </div>
          ))}
          <div style={s.holdingInputRow}>
            <input
              placeholder="TICK"
              value={newTicker}
              onChange={(e) => setNewTicker(e.target.value.toUpperCase())}
              style={{ ...s.holdingInput, width: "70px" }}
              maxLength={5}
            />
            <input
              placeholder="$price"
              value={newPrice}
              onChange={(e) => setNewPrice(e.target.value)}
              style={{ ...s.holdingInput, width: "80px" }}
              type="number"
              min="0"
            />
            <button onClick={addHolding} style={s.addBtn}>
              +
            </button>
          </div>
        </div>

        {/* Session controls */}
        <div style={{ marginTop: "auto", paddingTop: "1rem" }}>
          <button onClick={clearSession} style={s.clearBtn}>
            Clear Session
          </button>
          <button
            onClick={() => setApiKey(null)}
            style={{ ...s.clearBtn, marginTop: "8px", color: "#ff5f57" }}
          >
            Change API Key
          </button>
        </div>
      </aside>

      {/* ── Main chat ── */}
      <main style={s.main}>
        {/* Chat messages */}
        <div style={s.chatArea}>
          {chat.length === 0 && (
            <div style={s.emptyState}>
              <div style={s.emptyIcon}>⬡</div>
              <div style={s.emptyTitle}>Stock Analyst Ready</div>
              <div style={s.emptyHint}>
                Ask about any stock or choose a quick prompt from the sidebar.
              </div>
            </div>
          )}

          {chat.map((entry, i) => (
            <div key={i} style={entry.role === "user" ? s.userBubble : s.aiBubble}>
              <div style={s.bubbleLabel}>
                {entry.role === "user" ? "YOU" : "AI ANALYST"}
              </div>
              <div style={s.bubbleText}>{entry.content}</div>
              {entry.response && entry.response.recommendations.length > 0 && (
                <StockTable recommendations={entry.response.recommendations} />
              )}
              {entry.response && (
                <div style={s.metaRow}>
                  <span style={s.metaBadge}>
                    {entry.response.tool_calls_made} searches
                  </span>
                  <span style={s.metaBadge}>
                    {entry.response.iterations} iterations
                  </span>
                  <span style={s.metaBadge}>{entry.response.mode} mode</span>
                </div>
              )}
            </div>
          ))}

          {loading && (
            <div style={s.aiBubble}>
              <div style={s.bubbleLabel}>AI ANALYST</div>
              <div style={s.loadingDots}>
                <span>●</span>
                <span>●</span>
                <span>●</span>
              </div>
            </div>
          )}
          <div ref={bottomRef} />
        </div>

        {/* Input bar */}
        <div style={s.inputBar}>
          <div style={s.modePill}>
            {mode === "general" ? "Market" : "Stock"}
          </div>
          <input
            style={s.textInput}
            placeholder={
              mode === "individual"
                ? "e.g. Should I buy NVDA?"
                : "e.g. What AI stocks look good?"
            }
            value={message}
            onChange={(e) => setMessage(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && send(message)}
          />
          <button
            style={{
              ...s.sendBtn,
              opacity: loading || !message.trim() ? 0.5 : 1,
              cursor: loading || !message.trim() ? "not-allowed" : "pointer",
            }}
            onClick={() => send(message)}
            disabled={loading || !message.trim()}
          >
            ↑
          </button>
        </div>
      </main>

      <style>{`
        @keyframes blink {
          0%, 80%, 100% { opacity: 0.2; }
          40% { opacity: 1; }
        }
        .loading-dot { animation: blink 1.4s infinite both; }
        .loading-dot:nth-child(2) { animation-delay: 0.2s; }
        .loading-dot:nth-child(3) { animation-delay: 0.4s; }
      `}</style>
    </div>
  );
}

const s: Record<string, React.CSSProperties> = {
  root: {
    display: "flex",
    height: "100vh",
    background: "#0a0e1a",
    color: "#e2e8f0",
    fontFamily: "'Courier New', monospace",
    overflow: "hidden",
  },
  sidebar: {
    width: "240px",
    minWidth: "240px",
    background: "#0d1321",
    borderRight: "0.5px solid #1e3a5f",
    padding: "1.25rem 1rem",
    display: "flex",
    flexDirection: "column",
    gap: "0",
    overflowY: "auto",
  },
  sidebarLogo: {
    fontSize: "16px",
    color: "#28c840",
    fontWeight: 500,
    marginBottom: "1.5rem",
  },
  section: {
    marginBottom: "1.5rem",
  },
  sectionLabel: {
    fontSize: "10px",
    color: "#4a9eff",
    letterSpacing: "0.1em",
    marginBottom: "8px",
  },
  modeRow: {
    display: "flex",
    gap: "6px",
  },
  modeBtn: {
    flex: 1,
    background: "transparent",
    border: "0.5px solid #1e3a5f",
    borderRadius: "6px",
    padding: "6px",
    color: "#64748b",
    fontSize: "11px",
    cursor: "pointer",
    fontFamily: "'Courier New', monospace",
  },
  modeBtnActive: {
    background: "#1e3a5f",
    color: "#4a9eff",
    borderColor: "#4a9eff",
  },
  quickBtn: {
    display: "block",
    width: "100%",
    background: "transparent",
    border: "none",
    color: "#64748b",
    fontSize: "11px",
    textAlign: "left",
    padding: "5px 0",
    cursor: "pointer",
    fontFamily: "'Courier New', monospace",
    lineHeight: 1.4,
    borderBottom: "0.5px solid #0f1c2e",
  },
  holdingRow: {
    display: "flex",
    alignItems: "center",
    gap: "6px",
    padding: "4px 0",
    borderBottom: "0.5px solid #0f1c2e",
  },
  holdingTicker: {
    color: "#4a9eff",
    fontSize: "12px",
    flex: 1,
  },
  holdingPrice: {
    color: "#febc2e",
    fontSize: "11px",
  },
  removeBtn: {
    background: "none",
    border: "none",
    color: "#475569",
    cursor: "pointer",
    fontSize: "11px",
    padding: "0 2px",
  },
  holdingInputRow: {
    display: "flex",
    gap: "4px",
    marginTop: "8px",
  },
  holdingInput: {
    background: "#0a0e1a",
    border: "0.5px solid #1e3a5f",
    borderRadius: "4px",
    padding: "5px 6px",
    color: "#e2e8f0",
    fontSize: "11px",
    fontFamily: "'Courier New', monospace",
    outline: "none",
  },
  addBtn: {
    background: "#1e3a5f",
    border: "none",
    borderRadius: "4px",
    color: "#4a9eff",
    width: "28px",
    cursor: "pointer",
    fontSize: "16px",
    fontFamily: "'Courier New', monospace",
  },
  clearBtn: {
    width: "100%",
    background: "transparent",
    border: "0.5px solid #1e3a5f",
    borderRadius: "6px",
    padding: "7px",
    color: "#475569",
    fontSize: "11px",
    cursor: "pointer",
    fontFamily: "'Courier New', monospace",
  },
  main: {
    flex: 1,
    display: "flex",
    flexDirection: "column",
    overflow: "hidden",
  },
  chatArea: {
    flex: 1,
    overflowY: "auto",
    padding: "1.5rem",
    display: "flex",
    flexDirection: "column",
    gap: "1.25rem",
  },
  emptyState: {
    flex: 1,
    display: "flex",
    flexDirection: "column",
    alignItems: "center",
    justifyContent: "center",
    margin: "auto",
    textAlign: "center",
    padding: "3rem 0",
  },
  emptyIcon: {
    fontSize: "48px",
    color: "#1e3a5f",
    marginBottom: "1rem",
  },
  emptyTitle: {
    fontSize: "18px",
    color: "#28c840",
    marginBottom: "8px",
  },
  emptyHint: {
    fontSize: "13px",
    color: "#475569",
    maxWidth: "320px",
    lineHeight: 1.6,
  },
  userBubble: {
    alignSelf: "flex-end",
    maxWidth: "75%",
    background: "#111827",
    border: "0.5px solid #1e3a5f",
    borderRadius: "12px 12px 2px 12px",
    padding: "0.75rem 1rem",
  },
  aiBubble: {
    alignSelf: "flex-start",
    maxWidth: "95%",
    background: "#0d1321",
    border: "0.5px solid #1e3a5f",
    borderRadius: "2px 12px 12px 12px",
    padding: "0.75rem 1rem",
  },
  bubbleLabel: {
    fontSize: "10px",
    color: "#4a9eff",
    letterSpacing: "0.08em",
    marginBottom: "6px",
  },
  bubbleText: {
    fontSize: "13px",
    color: "#cbd5e1",
    lineHeight: 1.7,
    whiteSpace: "pre-wrap",
  },
  loadingDots: {
    display: "flex",
    gap: "6px",
    padding: "4px 0",
    fontSize: "18px",
    color: "#28c840",
  },
  metaRow: {
    display: "flex",
    gap: "8px",
    marginTop: "10px",
    flexWrap: "wrap",
  },
  metaBadge: {
    fontSize: "10px",
    color: "#475569",
    background: "#0a0e1a",
    border: "0.5px solid #1e3a5f",
    borderRadius: "4px",
    padding: "2px 6px",
  },
  inputBar: {
    display: "flex",
    alignItems: "center",
    gap: "8px",
    padding: "1rem 1.25rem",
    borderTop: "0.5px solid #1e3a5f",
    background: "#0d1321",
  },
  modePill: {
    fontSize: "10px",
    color: "#4a9eff",
    background: "#1e3a5f",
    borderRadius: "4px",
    padding: "4px 8px",
    whiteSpace: "nowrap",
  },
  textInput: {
    flex: 1,
    background: "#0a0e1a",
    border: "0.5px solid #1e3a5f",
    borderRadius: "8px",
    padding: "10px 14px",
    color: "#e2e8f0",
    fontFamily: "'Courier New', monospace",
    fontSize: "13px",
    outline: "none",
  },
  sendBtn: {
    background: "#4a9eff",
    border: "none",
    borderRadius: "8px",
    width: "38px",
    height: "38px",
    color: "#0a0e1a",
    fontSize: "18px",
    fontWeight: 700,
    cursor: "pointer",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
  },
};
