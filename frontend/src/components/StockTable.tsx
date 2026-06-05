import type { Recommendation, StockRecommendation } from "../types";

// ── Helpers ───────────────────────────────────────────────────────────────────

const REC_STYLES: Record<Recommendation, { bg: string; color: string; border: string }> = {
  "STRONG BUY":  { bg: "#0a2e1a", color: "#28c840", border: "#28c84055" },
  "GOOD BUY":    { bg: "#0a2010", color: "#5dde82", border: "#5dde8244" },
  "HOLD":        { bg: "#2a2200", color: "#febc2e", border: "#febc2e44" },
  "GOOD SELL":   { bg: "#2a1000", color: "#ff8c69", border: "#ff8c6944" },
  "STRONG SELL": { bg: "#2a0808", color: "#ff5f57", border: "#ff5f5755" },
};

// ── RecBadge ──────────────────────────────────────────────────────────────────

interface RecBadgeProps { rec: Recommendation }

export function RecBadge({ rec }: RecBadgeProps) {
  const s = REC_STYLES[rec] ?? REC_STYLES["HOLD"];
  return (
    <span style={{
      display: "inline-block",
      padding: "3px 9px",
      borderRadius: 3,
      fontSize: 10,
      fontWeight: "bold",
      letterSpacing: 1,
      whiteSpace: "nowrap",
      background: s.bg,
      color: s.color,
      border: `1px solid ${s.border}`,
      fontFamily: "'Courier New', monospace",
    }}>
      {rec}
    </span>
  );
}

// ── ConfidenceBar ─────────────────────────────────────────────────────────────

interface ConfidenceBarProps { value: number }

export function ConfidenceBar({ value }: ConfidenceBarProps) {
  const color = value >= 80 ? "#28c840" : value >= 60 ? "#febc2e" : "#ff5f57";
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
      <div style={{
        flex: 1, height: 4, background: "#1e3a5f33", borderRadius: 2, overflow: "hidden",
      }}>
        <div style={{ width: `${value}%`, height: "100%", background: color, borderRadius: 2 }} />
      </div>
      <span style={{ fontSize: 11, color, fontFamily: "'Courier New', monospace", minWidth: 32 }}>
        {value}%
      </span>
    </div>
  );
}

// ── StockTable ────────────────────────────────────────────────────────────────

interface StockTableProps { recommendations: StockRecommendation[] }

export function StockTable({ recommendations }: StockTableProps) {
  if (!recommendations.length) return null;

  return (
    <div style={{ overflowX: "auto", marginTop: 16 }}>
      <table style={{
        width: "100%",
        borderCollapse: "collapse",
        fontSize: 12,
        fontFamily: "'Courier New', monospace",
        minWidth: 720,
      }}>
        <thead>
          <tr>
            {["Ticker","Company","Price","Recommendation","Basis","Target","Valid Until","Confidence"].map(h => (
              <th key={h} style={{
                padding: "8px 12px",
                textAlign: "left",
                fontSize: 9,
                letterSpacing: 2,
                color: "#4a6fa5",
                borderBottom: "1px solid #1e3a5f",
                textTransform: "uppercase",
                whiteSpace: "nowrap",
                background: "#0d1117",
              }}>{h}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {recommendations.map((r) => (
            <tr key={r.ticker} style={{ cursor: "default" }}
              onMouseEnter={e => (e.currentTarget.style.background = "#0f1a2e")}
              onMouseLeave={e => (e.currentTarget.style.background = "transparent")}
            >
              <td style={td()}><span style={{ color: "#4a9eff", fontWeight: "bold", fontSize: 13, letterSpacing: 1 }}>{r.ticker}</span></td>
              <td style={td()}><span style={{ color: "#8892a4", fontSize: 11 }}>{r.name}</span></td>
              <td style={td()}><span style={{ fontVariantNumeric: "tabular-nums" }}>{r.current_price}</span></td>
              <td style={td()}><RecBadge rec={r.recommendation} /></td>
              <td style={{ ...td(), maxWidth: 220, color: "#8892a4", lineHeight: 1.5 }}>{r.reason}</td>
              <td style={{ ...td(), color: "#febc2e", fontVariantNumeric: "tabular-nums" }}>{r.target_price}</td>
              <td style={{ ...td(), color: "#5d7a9a", fontSize: 11 }}>{r.valid_until}</td>
              <td style={{ ...td(), minWidth: 120 }}><ConfidenceBar value={r.confidence} /></td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function td(): React.CSSProperties {
  return {
    padding: "10px 12px",
    borderBottom: "1px solid #111827",
    verticalAlign: "top",
    color: "#c8d3e0",
  };
}
