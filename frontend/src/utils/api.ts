import type { AnalysisRequest, AgentResponse } from "../types";

const BASE_URL = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

export async function analyze(request: AnalysisRequest): Promise<AgentResponse> {
  const res = await fetch(`${BASE_URL}/api/analyze`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(request),
  });
  if (!res.ok) {
    const detail = await res.text();
    throw new Error(`API error ${res.status}: ${detail}`);
  }
  return res.json();
}

export async function createSession(): Promise<string> {
  const res = await fetch(`${BASE_URL}/api/session/new`, { method: "POST" });
  const data = await res.json();
  return data.session_id;
}

export async function clearSession(sessionId: string): Promise<void> {
  await fetch(`${BASE_URL}/api/session/${sessionId}`, { method: "DELETE" });
}
