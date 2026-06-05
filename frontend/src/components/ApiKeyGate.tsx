import { useState } from "react";

interface Props {
  onKeySubmit: (key: string) => void;
}

export default function ApiKeyGate({ onKeySubmit }: Props) {
  const [key, setKey] = useState("");
  const [show, setShow] = useState(false);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const handleSubmit = async () => {
    const trimmed = key.trim();
    if (!trimmed.startsWith("sk-ant-")) {
      setError("Key must start with sk-ant-");
      return;
    }
    setError("");
    setLoading(true);
    // Small delay to show loading state
    await new Promise((r) => setTimeout(r, 400));
    setLoading(false);
    onKeySubmit(trimmed);
  };

  return (
    <div style={styles.wrapper}>
      <div style={styles.box}>
        {/* Header */}
        <div style={styles.header}>
          <div style={styles.logo}>⬡ Stock Analyst</div>
          <div style={styles.tagline}>AI-powered market intelligence</div>
        </div>

        {/* Card */}
        <div style={styles.card}>
          <label style={styles.label}>ANTHROPIC API KEY</label>

          <div style={styles.inputRow}>
            <input
              type={show ? "text" : "password"}
              placeholder="sk-ant-..."
              value={key}
              onChange={(e) => {
                setKey(e.target.value);
                setError("");
              }}
              onKeyDown={(e) => e.key === "Enter" && handleSubmit()}
              style={styles.input}
              autoComplete="off"
              spellCheck={false}
            />
            <button
              onClick={() => setShow(!show)}
              style={styles.eyeBtn}
              aria-label={show ? "Hide key" : "Show key"}
            >
              {show ? "🙈" : "👁"}
            </button>
          </div>

          {error && <p style={styles.error}>✗ {error}</p>}

          <p style={styles.hint}>
            🔒 Stored in memory only — never saved to disk or sent to our servers
          </p>

          <button
            onClick={handleSubmit}
            disabled={loading || !key.trim()}
            style={{
              ...styles.submitBtn,
              opacity: loading || !key.trim() ? 0.6 : 1,
              cursor: loading || !key.trim() ? "not-allowed" : "pointer",
            }}
          >
            {loading ? "CONNECTING..." : "CONNECT →"}
          </button>
        </div>

        {/* Footer */}
        <p style={styles.footer}>
          Get your key at{" "}
          <a
            href="https://console.anthropic.com"
            target="_blank"
            rel="noreferrer"
            style={styles.link}
          >
            console.anthropic.com
          </a>
        </p>
      </div>
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {
  wrapper: {
    minHeight: "100vh",
    background: "#0a0e1a",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    padding: "2rem",
    fontFamily: "'Courier New', monospace",
  },
  box: {
    width: "100%",
    maxWidth: "420px",
  },
  header: {
    textAlign: "center",
    marginBottom: "2rem",
  },
  logo: {
    fontSize: "24px",
    color: "#28c840",
    fontWeight: 500,
    marginBottom: "8px",
  },
  tagline: {
    fontSize: "13px",
    color: "#4a9eff",
  },
  card: {
    background: "#111827",
    border: "0.5px solid #1e3a5f",
    borderRadius: "12px",
    padding: "1.5rem",
  },
  label: {
    display: "block",
    fontSize: "11px",
    color: "#4a9eff",
    letterSpacing: "0.08em",
    marginBottom: "8px",
  },
  inputRow: {
    position: "relative",
    display: "flex",
    alignItems: "center",
  },
  input: {
    width: "100%",
    background: "#0a0e1a",
    border: "0.5px solid #1e3a5f",
    borderRadius: "8px",
    padding: "10px 40px 10px 12px",
    fontFamily: "'Courier New', monospace",
    fontSize: "13px",
    color: "#e2e8f0",
    outline: "none",
    boxSizing: "border-box",
  },
  eyeBtn: {
    position: "absolute",
    right: "10px",
    background: "none",
    border: "none",
    cursor: "pointer",
    fontSize: "16px",
    padding: 0,
    lineHeight: 1,
  },
  error: {
    margin: "8px 0 0",
    fontSize: "11px",
    color: "#ff5f57",
  },
  hint: {
    margin: "10px 0 0",
    fontSize: "11px",
    color: "#475569",
    lineHeight: 1.5,
  },
  submitBtn: {
    marginTop: "1.25rem",
    width: "100%",
    background: "#4a9eff",
    border: "none",
    borderRadius: "8px",
    padding: "11px",
    fontFamily: "'Courier New', monospace",
    fontSize: "13px",
    color: "#0a0e1a",
    fontWeight: 500,
    letterSpacing: "0.05em",
    transition: "opacity 0.2s",
  },
  footer: {
    textAlign: "center",
    marginTop: "1rem",
    fontSize: "11px",
    color: "#334155",
  },
  link: {
    color: "#4a9eff",
    textDecoration: "none",
  },
};
