// ── Enums ─────────────────────────────────────────────────────────────────────

export type AgentMode = "individual" | "general";

export type Recommendation =
  | "STRONG BUY"
  | "GOOD BUY"
  | "HOLD"
  | "GOOD SELL"
  | "STRONG SELL";

// ── Request / response ────────────────────────────────────────────────────────

export interface HoldingContext {
  ticker: string;
  buy_price?: number;
  quantity?: number;
  buy_date?: string;
}

export interface ChatMessage {
  role: "user" | "assistant";
  content: string;
}

export interface AnalysisRequest {
  message: string;
  mode: AgentMode;
  session_id: string;
  conversation_history: ChatMessage[];
  known_holdings: HoldingContext[];
}

export interface StockRecommendation {
  ticker: string;
  name: string;
  current_price: string;
  recommendation: Recommendation;
  reason: string;
  target_price: string;
  valid_until: string;
  confidence: number;
  catalysts: string[];
  risks: string[];
  user_pnl_pct?: number;
}

export interface AgentResponse {
  session_id: string;
  mode: AgentMode;
  narrative: string;
  recommendations: StockRecommendation[];
  tool_calls_made: number;
  iterations: number;
  raw_assistant_text: string;
}

// ── UI state ──────────────────────────────────────────────────────────────────

export interface ConversationTurn {
  id: string;
  role: "user" | "assistant";
  text: string;
  response?: AgentResponse;
  timestamp: Date;
  loading?: boolean;
}
