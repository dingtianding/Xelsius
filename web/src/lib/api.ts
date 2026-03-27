import type { AuditEntry, RunResponse } from "./types";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8888";

export async function runAgent(prompt: string): Promise<RunResponse> {
  const res = await fetch(`${API_BASE}/agent/run`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ prompt }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "Request failed" }));
    throw new Error(err.detail ?? "Request failed");
  }
  return res.json();
}

export async function getAuditLog(): Promise<AuditEntry[]> {
  const res = await fetch(`${API_BASE}/audit/log`);
  if (!res.ok) throw new Error("Failed to fetch audit log");
  return res.json();
}
