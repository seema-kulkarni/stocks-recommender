# Stock Analyst Agent

A multi-agent AI system for real-time stock market analysis and recommendations, built on the Anthropic Claude API.

## Architecture

```
User Prompt
    │
    ▼
Orchestrator Agent          ← intent parsing, session memory, routing
    │
    ├─► Intent Router        ← classify_intent + extract_holdings tools
    │
    ├─► Individual Stock Agent   ← deep-dives a single ticker
    │       └─► ReAct Loop (Think → Act → Observe → Judge)
    │
    └─► General Market Agent     ← analyses a basket of AI/quantum/S&P stocks
            └─► ReAct Loop (Think → Act → Observe → Judge)
                    │
                    ▼
             Tool Registry
             ├── web_search (Anthropic built-in)
             ├── Price fetcher  (NYSE · NASDAQ · Google Finance)
             ├── News scraper   (CNBC · Yahoo · X · Reddit)
             └── Analyst data   (TipRanks · Zacks · Morningstar)
                    │
                    ▼
             Session Memory (Redis / in-process)
             └── Holdings · Conversation · Ticker cache
```

## Quickstart

### Prerequisites
- Python 3.12+
- Node 20+
- An Anthropic API key (`ANTHROPIC_API_KEY`)
- Redis (optional — falls back to in-memory store)

---

### 1. Backend

```bash
cd backend

# Copy and fill in your API key
cp .env.example .env
# Edit .env: set ANTHROPIC_API_KEY=sk-ant-...

# Install dependencies
pip install -r requirements.txt

# Run
python main.py
# → API live at http://localhost:8000
# → Docs at  http://localhost:8000/docs
```

### 2. Frontend

```bash
cd frontend
npm install
npm run dev
# → http://localhost:3000
```

### 3. Docker (full stack)

```bash
# From the repo root
echo "ANTHROPIC_API_KEY=sk-ant-..." > .env
docker compose up --build
# Backend: http://localhost:8000
# Frontend: http://localhost:3000
```

---

## API Reference

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/analyze` | Main analysis endpoint |
| `GET` | `/api/session/{id}` | Fetch session memory |
| `DELETE` | `/api/session/{id}` | Clear session |
| `POST` | `/api/session/new` | Generate session ID |
| `GET` | `/api/health` | Liveness probe |

### POST /api/analyze — request body

```json
{
  "message": "Should I buy DELL?",
  "mode": "individual",
  "session_id": "uuid-here",
  "conversation_history": [],
  "known_holdings": [
    { "ticker": "DELL", "buy_price": 467.00 }
  ]
}
```

### Response

```json
{
  "session_id": "...",
  "mode": "individual",
  "narrative": "Dell reported Q1 FY2027...",
  "recommendations": [
    {
      "ticker": "DELL",
      "name": "Dell Technologies",
      "current_price": "$435.31",
      "recommendation": "GOOD BUY",
      "reason": "Strong AI server backlog...",
      "target_price": "$500",
      "valid_until": "Q3 2026 earnings",
      "confidence": 78,
      "catalysts": ["$51.3B backlog", "Goldman $500 target"],
      "risks": ["198% premium to intrinsic value", "Insider selling"]
    }
  ],
  "tool_calls_made": 4,
  "iterations": 2
}
```

---

## Configuration

All settings are in `backend/.env`:

| Variable | Default | Description |
|----------|---------|-------------|
| `ANTHROPIC_API_KEY` | — | Required |
| `REDIS_URL` | `redis://localhost:6379` | Falls back to in-process dict |
| `AGENT_MODEL` | `claude-sonnet-4-20250514` | Claude model for all agents |
| `MAX_REACT_ITERATIONS` | `3` | Max ReAct loop iterations per query |
| `MIN_CONFIDENCE` | `65` | Minimum confidence score to emit a rec |
| `TOOL_CACHE_TTL` | `900` | Tool result cache TTL in seconds (15 min) |

---

## Project Structure

```
stock-agent/
├── backend/
│   ├── agents/
│   │   ├── base.py          # BaseAgent — shared ReAct loop
│   │   ├── orchestrator.py  # Top-level router + memory manager
│   │   ├── individual.py    # Single-stock specialist
│   │   ├── general.py       # Market basket specialist
│   │   └── prompts.py       # System prompt templates
│   ├── tools/
│   │   └── registry.py      # Tool definitions, watchlists, cache
│   ├── memory/
│   │   └── manager.py       # Redis / in-process session store
│   ├── models/
│   │   └── schemas.py       # Pydantic data models
│   ├── api/
│   │   └── app.py           # FastAPI routes
│   ├── config.py            # Settings (pydantic-settings)
│   ├── main.py              # Uvicorn entry point
│   └── requirements.txt
│
├── frontend/
│   └── src/
│       ├── App.tsx           # Main UI — chat + analysis dashboard
│       ├── components/
│       │   └── StockTable.tsx # Rec table + badges + confidence bars
│       ├── utils/
│       │   └── api.ts        # Typed API client
│       └── types/
│           └── index.ts      # Shared TypeScript types
│
└── docker-compose.yml
```

---

## Extending the Agent

### Add a new stock to the watchlist
Edit `backend/tools/registry.py` — add to `SP500_AI_WATCHLIST`, `QUANTUM_WATCHLIST`, or `AI_WATCHLIST`.

### Add a new tool
1. Add the tool schema to `CUSTOM_TOOLS` in `registry.py`
2. Handle it in `BaseAgent._dispatch_tool()` in `base.py`
3. Add it to `ALL_TOOLS`

### Add a new sub-agent (e.g. crypto, ETFs)
1. Create `backend/agents/crypto.py` inheriting from `BaseAgent`
2. Add a system prompt in `prompts.py`
3. Register it in `Orchestrator.handle()` with a new `AgentMode` enum value

---

## Disclaimer

This system is for **informational purposes only** and does not constitute financial advice.
Always consult a licensed financial advisor before making investment decisions.
