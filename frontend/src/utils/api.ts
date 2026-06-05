import type { AnalysisRequest, AgentResponse } from "../types";

const BASE_URL = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

export async function analyzeStock(
  request: AnalysisRequest,
  apiKey: string
): Promise<AgentResponse> {
  const res = await fetch(`${BASE_URL}/api/analyze`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-API-Key": apiKey,
    },
    body: JSON.stringify(request),
  });

  if (!res.ok) {
    const detail = await res.text().catch(() => res.statusText);
    throw new Error(`API error ${res.status}: ${detail}`);
  }

  return res.json() as Promise<AgentResponse>;
}

export async function getSession(sessionId: string, apiKey: string) {
  const res = await fetch(`${BASE_URL}/api/session/${sessionId}`, {
    headers: { "X-API-Key": apiKey },
  });
  if (!res.ok) throw new Error(`Session fetch failed: ${res.status}`);
  return res.json();
}

export async function deleteSession(sessionId: string, apiKey: string) {
  const res = await fetch(`${BASE_URL}/api/session/${sessionId}`, {
    method: "DELETE",
    headers: { "X-API-Key": apiKey },
  });
  if (!res.ok) throw new Error(`Session delete failed: ${res.status}`);
  return res.json();
}

export async function newSession(apiKey: string): Promise<{ session_id: string }> {
  const res = await fetch(`${BASE_URL}/api/session/new`, {
    method: "POST",
    headers: { "X-API-Key": apiKey },
  });
  if (!res.ok) throw new Error(`New session failed: ${res.status}`);
  return res.json();
}

export async function healthCheck(): Promise<{ status: string }> {
  const res = await fetch(`${BASE_URL}/api/health`);
  if (!res.ok) throw new Error("Health check failed");
  return res.json();
}
