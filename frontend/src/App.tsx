import { useState, useEffect, useRef, useCallback } from "react";
import { v4 as uuidv4 } from "uuid";
import { analyze, createSession, clearSession } from "./utils/api";
import { StockTable } from "./components/StockTable";
import type {
  AgentMode, ConversationTurn, HoldingContext, ChatMessage, AgentResponse,
} from "./types";

// ── Quick prompts ─────────────────────────────────────────────────────────────

const QUICK_PROMPTS = [
  "What AI stocks should I buy right now?",
  "Which stocks should I sell or avoid?",
  "Analyze all quantum computing stocks",
  "Best S&P 500 tech stocks this week?",
  "Overall market outlook for AI sector?",
];

const SIDEBAR_STOCKS = [
  { ticker: "DELL",  label: "Dell Technologies" },
  { ticker: "ARM",   label: "Arm Holdings" },
  { ticker: "AMD",   label: "Advanced Micro Devices" },
  { ticker: "INTC",  label: "Intel Corp" },
  { ticker: "NOW",   label: "ServiceNow" },
  { ticker: "AMZN",  label: "Amazon" },
  { ticker: "MSFT",  label: "Microsoft" },
  { ticker: "GOOGL", label: "Alphabet" },
  { ticker: "NVDA",  label: "NVIDIA" },
  { ticker: "PLTR",  label: "Palantir" },
  { ticker: "IONQ",  label: "IonQ" },
  { ticker: "NBIS",  label: "Nebius Group" },
  { ticker: "MU",    label: "Micron Technology" },
  { ticker: "MRVL",  label: "Marvell Technology" },
];

// ── App ───────────────────────────────────────────────────────────────────────

export default function App() {
  const [sessionId, setSessionId] = useState<string>("");
  const [mode, setMode]           = useState<AgentMode>("general");
  const [turns, setTurns]         = useState<ConversationTurn[]>([]);
  const [input, setInput]         = useState("");
  const [loading, setLoading]     = useState(false);
  const [holdings, setHoldings]   = useState<HoldingContext[]>([]);
  const chatRef = useRef<HTMLDivElement>(null);

  // Initialise session
  useEffect(() => {
    const stored = sessionStorage.getItem("stock_session_id");
    if (stored) { setSessionId(stored); return; }
    createSession().then(id => {
      setSessionId(id);
      sessionStorage.setItem("stock_session_id", id);
    });
  }, []);

  // Auto-scroll
  useEffect(() => {
    chatRef.current?.scrollTo({ top: chatRef.current.scrollHeight, behavior: "smooth" });
  }, [turns]);

  const send = useCallback(async (message: string) => {
    if (!message.trim() || loading || !sessionId) return;
    setInput("");
    setLoading(true);

    const userTurn: ConversationTurn = {
      id: uuidv4(), role: "user", text: message, timestamp: new Date(),
    };
    const loadingTurn: ConversationTurn = {
      id: uuidv4(), role: "assistant", text: "", timestamp: new Date(), loading: true,
    };
    setTurns(prev => [...prev, userTurn, loadingTurn]);

    const history: ChatMessage[] = turns
      .filter(t => !t.loading)
      .slice(-10)
      .map(t => ({ role: t.role, content: t.text }));

    try {
      const response = await analyze({
        message,
        mode,
        session_id: sessionId,
        conversation_history: history,
        known_holdings: holdings,
      });

      // Extract any new holdings from the response and persist locally
      const newHoldings = extractHoldingsFromResponse(response, message);
      if (newHoldings.length) {
        setHoldings(prev => {
          const merged = [...prev];
          for (const h of newHoldings) {
            const idx = merged.findIndex(x => x.ticker === h.ticker);
            if (idx >= 0) merged[idx] = h; else merged.push(h);
          }
          return merged;
        });
      }

      const assistantTurn: ConversationTurn = {
        id: uuidv4(),
        role: "assistant",
        text: response.narrative || response.raw_assistant_text || "",
        response,
        timestamp: new Date(),
      };
      setTurns(prev => [...prev.filter(t => !t.loading), assistantTurn]);
    } catch (err: any) {
      const errorTurn: ConversationTurn = {
        id: uuidv4(),
        role: "assistant",
        text: `⚠ Error: ${err.message ?? "Unknown error"}`,
        timestamp: new Date(),
      };
      setTurns(prev => [...prev.filter(t => !t.loading), errorTurn]);
    } finally {
      setLoading(false);
    }
  }, [loading, sessionId, mode, turns, holdings]);

  const handleReset = async () => {
    if (!sessionId) return;
    await clearSession(sessionId);
    sessionStorage.removeItem("stock_session_id");
    const newId = await createSession();
    setSessionId(newId);
    sessionStorage.setItem("stock_session_id", newId);
    setTurns([]);
    setHoldings([]);
  };

  return (
    <div style={styles.shell}>
      {/* ── Title bar ── */}
      <div style={styles.titleBar}>
        <div style={styles.dots}>
          <span style={{ ...styles.dot, background: "#ff5f57" }} />
          <span style={{ ...styles.dot, background: "#febc2e" }} />
          <span style={{ ...styles.dot, background: "#28c840" }} />
        </div>
        <span style={styles.titleText}>STOCK ANALYST AGENT v1.0</span>
        <div style={styles.liveBadge}>
          <span style={styles.liveDot} />
          LIVE AI ANALYSIS
        </div>
      </div>

      <div style={styles.body}>
        {/* ── Sidebar ── */}
        <div style={styles.sidebar}>
          <div style={styles.sectionLabel}>Mode</div>
          <SidebarBtn active={mode === "general"} onClick={() => setMode("general")}>
            ◈ General Market
          </SidebarBtn>
          <SidebarBtn active={mode === "individual"} onClick={() => setMode("individual")}>
            ◉ Individual Stock
          </SidebarBtn>

          <div style={styles.sectionLabel}>Watchlist</div>
          {SIDEBAR_STOCKS.map(s => (
            <button key={s.ticker} style={styles.stockChip}
              onClick={() => {
                setMode("individual");
                setInput(`Analyze ${s.ticker} — should I buy, sell, or hold?`);
              }}
            >
              <span style={{ color: "#4a9eff", fontWeight: "bold" }}>{s.ticker}</span>
              <span style={{ color: "#3d5a8a", fontSize: 9 }}>{s.label}</span>
            </button>
          ))}

          {holdings.length > 0 && (
            <>
              <div style={styles.sectionLabel}>My Holdings</div>
              {holdings.map(h => (
                <div key={h.ticker} style={styles.holdingChip}>
                  <span style={{ color: "#28c840" }}>{h.ticker}</span>
                  {h.buy_price && <span style={{ color: "#4a6fa5", fontSize: 9 }}>${h.buy_price}</span>}
                </div>
              ))}
            </>
          )}

          <div style={{ flex: 1 }} />
          <button style={styles.resetBtn} onClick={handleReset}>↺ Reset Session</button>
        </div>

        {/* ── Main panel ── */}
        <div style={styles.main}>
          {/* Mode header */}
          <div style={styles.modeHeader}>
            <div style={{ color: "#4a9eff", fontSize: 13, fontWeight: "bold", letterSpacing: 1 }}>
              {mode === "general" ? "◈ GENERAL MARKET ANALYSIS" : "◉ INDIVIDUAL STOCK ANALYSIS"}
            </div>
            <div style={{ color: "#4a6fa5", fontSize: 11, marginTop: 2 }}>
              {mode === "general"
                ? "Analyses S&P 500, quantum & AI stocks with buy/sell/hold recommendations"
                : "Deep dive into a single stock — trends, news, and personalised recommendation"}
            </div>
          </div>

          {/* Chat area */}
          <div ref={chatRef} style={styles.chat}>
            {/* Welcome message */}
            {turns.length === 0 && (
              <div style={styles.welcomeMsg}>
                <div style={styles.avatar}>AI</div>
                <div>
                  <div style={styles.msgLabel}>Stock Analyst Agent</div>
                  <div style={styles.msgText}>
                    Welcome. I use live web data and AI reasoning to analyse stocks across the
                    S&P 500, quantum computing sector, and AI ecosystem.
                    Ask me anything — "What stocks should I buy?", "Should I sell my NVDA?",
                    or click a ticker in the sidebar.
                  </div>
                </div>
              </div>
            )}

            {/* Conversation turns */}
            {turns.map(turn => (
              <div key={turn.id} style={styles.turn}>
                <div style={{
                  ...styles.avatar,
                  background: turn.role === "user" ? "#1e3a5f" : "#1a2e1a",
                  color: turn.role === "user" ? "#4a9eff" : "#28c840",
                }}>
                  {turn.role === "user" ? "YOU" : "AI"}
                </div>
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={styles.msgLabel}>
                    {turn.role === "user" ? "You" : "Stock Analyst Agent"}
                  </div>

                  {turn.loading ? (
                    <div style={styles.thinking}>
                      <span>Searching live market data</span>
                      <ThinkingDots />
                    </div>
                  ) : (
                    <>
                      <div style={{
                        ...styles.msgText,
                        color: turn.role === "user" ? "#8fafd6" : "#c8d3e0",
                        whiteSpace: "pre-wrap",
                      }}>
                        {turn.text}
                      </div>

                      {turn.response?.recommendations?.length > 0 && (
                        <>
                          <StockTable recommendations={turn.response.recommendations} />
                          <div style={styles.disclaimer}>
                            ⚠️ AI-generated analysis using live web data. Not financial advice.
                            Always consult a licensed financial advisor before investing.
                            {turn.response.tool_calls_made > 0 &&
                              ` (${turn.response.tool_calls_made} tool calls, ${turn.response.iterations} iterations)`}
                          </div>
                        </>
                      )}
                    </>
                  )}
                </div>
              </div>
            ))}
          </div>

          {/* Input area */}
          <div style={styles.inputArea}>
            <div style={styles.quickBtns}>
              {QUICK_PROMPTS.map(p => (
                <button key={p} style={styles.quickBtn} onClick={() => send(p)}>{p}</button>
              ))}
            </div>
            <div style={{ display: "flex", gap: 10 }}>
              <textarea
                style={styles.textarea}
                value={input}
                onChange={e => setInput(e.target.value)}
                onKeyDown={e => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); send(input); } }}
                placeholder='Ask about stocks... e.g. "Should I buy DELL?" or "Good AI stocks?"'
                rows={1}
                disabled={loading}
              />
              <button
                style={{ ...styles.sendBtn, opacity: loading ? 0.5 : 1 }}
                onClick={() => send(input)}
                disabled={loading}
              >
                ANALYZE ↗
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

// ── Small components ──────────────────────────────────────────────────────────

function SidebarBtn({ active, onClick, children }: {
  active: boolean; onClick: () => void; children: React.ReactNode;
}) {
  return (
    <button style={{
      ...styles.modeBtn,
      background: active ? "#1e3a5f44" : "transparent",
      color: active ? "#4a9eff" : "#8892a4",
      border: `1px solid ${active ? "#1e3a5f" : "transparent"}`,
    }} onClick={onClick}>
      {children}
    </button>
  );
}

function ThinkingDots() {
  return (
    <span style={{ display: "inline-flex", gap: 3, marginLeft: 8 }}>
      {[0, 1, 2].map(i => (
        <span key={i} style={{
          width: 5, height: 5, borderRadius: "50%", background: "#4a9eff",
          display: "inline-block",
          animation: `bounce 1.2s infinite ${i * 0.2}s`,
        }} />
      ))}
    </span>
  );
}

// ── Helpers ───────────────────────────────────────────────────────────────────

function extractHoldingsFromResponse(response: AgentResponse, message: string): HoldingContext[] {
  const holdings: HoldingContext[] = [];
  const tickerMatch = message.match(/\b([A-Z]{2,5})\b/g);
  const priceMatch = message.match(/\$?([\d,]+(?:\.\d+)?)/);
  if (tickerMatch && (message.toLowerCase().includes("hold") ||
    message.toLowerCase().includes("bought") || message.toLowerCase().includes("own"))) {
    for (const ticker of tickerMatch.slice(0, 3)) {
      holdings.push({
        ticker,
        buy_price: priceMatch ? parseFloat(priceMatch[1].replace(",", "")) : undefined,
      });
    }
  }
  return holdings;
}

// ── Styles ────────────────────────────────────────────────────────────────────

const styles: Record<string, React.CSSProperties> = {
  shell: {
    display: "flex", flexDirection: "column", height: "100vh",
    background: "#0a0e1a", color: "#e2e8f0",
    fontFamily: "'Courier New', monospace",
  },
  titleBar: {
    background: "#0d1117", borderBottom: "1px solid #1e3a5f",
    padding: "10px 20px", display: "flex", alignItems: "center", gap: 12, flexShrink: 0,
  },
  dots: { display: "flex", gap: 6 },
  dot: { width: 12, height: 12, borderRadius: "50%" },
  titleText: { color: "#4a9eff", fontSize: 12, letterSpacing: 2, fontWeight: "bold" },
  liveBadge: {
    marginLeft: "auto", display: "flex", alignItems: "center", gap: 6,
    fontSize: 11, color: "#28c840", letterSpacing: 1,
  },
  liveDot: {
    width: 7, height: 7, borderRadius: "50%", background: "#28c840",
    animation: "pulse 1.5s infinite",
  },
  body: { display: "flex", flex: 1, overflow: "hidden" },
  sidebar: {
    width: 220, background: "#0d1117", borderRight: "1px solid #1e3a5f",
    padding: "14px 0", display: "flex", flexDirection: "column",
    gap: 2, overflowY: "auto", flexShrink: 0,
  },
  sectionLabel: {
    padding: "8px 16px 4px", fontSize: 9, letterSpacing: 2,
    color: "#4a6fa5", textTransform: "uppercase",
  },
  modeBtn: {
    margin: "1px 8px", padding: "9px 12px", borderRadius: 6,
    cursor: "pointer", background: "transparent", color: "#8892a4",
    fontFamily: "'Courier New', monospace", fontSize: 12,
    textAlign: "left", transition: "all 0.2s", display: "flex", alignItems: "center", gap: 8,
  },
  stockChip: {
    margin: "1px 8px", padding: "5px 10px", borderRadius: 4, cursor: "pointer",
    border: "1px solid transparent", background: "transparent",
    fontFamily: "'Courier New', monospace", fontSize: 11,
    textAlign: "left", display: "flex", justifyContent: "space-between", alignItems: "center",
    color: "#6b7a94", transition: "all 0.2s",
  },
  holdingChip: {
    margin: "1px 8px", padding: "4px 10px", fontSize: 11,
    display: "flex", justifyContent: "space-between",
    background: "#0a1f0a", borderRadius: 4, border: "1px solid #28c84033",
  },
  resetBtn: {
    margin: "8px 10px 4px", padding: "7px 12px", borderRadius: 4,
    border: "1px solid #1e3a5f", background: "transparent", color: "#4a6fa5",
    fontFamily: "'Courier New', monospace", fontSize: 10, cursor: "pointer",
  },
  main: { display: "flex", flexDirection: "column", flex: 1, overflow: "hidden" },
  modeHeader: {
    padding: "14px 24px", borderBottom: "1px solid #1e3a5f", background: "#0d1117", flexShrink: 0,
  },
  chat: { flex: 1, overflowY: "auto", padding: "20px 24px", display: "flex", flexDirection: "column", gap: 16 },
  welcomeMsg: { display: "flex", gap: 10 },
  turn: { display: "flex", gap: 10 },
  avatar: {
    width: 32, height: 32, borderRadius: 4, display: "flex",
    alignItems: "center", justifyContent: "center",
    fontSize: 10, fontWeight: "bold", flexShrink: 0, marginTop: 2,
  },
  msgLabel: { fontSize: 10, letterSpacing: 1, color: "#4a6fa5", marginBottom: 4, textTransform: "uppercase" },
  msgText: { fontSize: 13, color: "#c8d3e0", lineHeight: 1.65 },
  thinking: {
    display: "flex", alignItems: "center", padding: "10px 14px",
    border: "1px solid #1e3a5f", borderRadius: 6, background: "#0d1117",
    fontSize: 12, color: "#4a9eff",
  },
  disclaimer: {
    marginTop: 10, padding: "8px 12px", border: "1px solid #1e3a5f",
    borderRadius: 5, background: "#0d1117", fontSize: 10, color: "#4a6fa5", lineHeight: 1.6,
  },
  inputArea: { padding: "14px 24px", borderTop: "1px solid #1e3a5f", background: "#0d1117", flexShrink: 0 },
  quickBtns: { display: "flex", gap: 6, marginBottom: 10, flexWrap: "wrap" },
  quickBtn: {
    background: "transparent", border: "1px solid #1e3a5f", borderRadius: 4,
    color: "#4a6fa5", fontFamily: "'Courier New', monospace", fontSize: 10,
    padding: "4px 10px", cursor: "pointer", transition: "all 0.2s",
  },
  textarea: {
    flex: 1, background: "#0a0e1a", border: "1px solid #1e3a5f", borderRadius: 6,
    padding: "10px 14px", color: "#e2e8f0", fontFamily: "'Courier New', monospace",
    fontSize: 13, resize: "none", outline: "none",
    minHeight: 42, maxHeight: 120,
  },
  sendBtn: {
    background: "#4a9eff", color: "#0a0e1a", border: "none", borderRadius: 6,
    padding: "10px 16px", fontFamily: "'Courier New', monospace", fontSize: 12,
    fontWeight: "bold", cursor: "pointer", letterSpacing: 1, whiteSpace: "nowrap",
  },
};
