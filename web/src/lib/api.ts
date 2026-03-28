import type { AuditEntry, RunResponse, UploadResponse } from "./types";

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

export async function uploadFile(file: File): Promise<UploadResponse> {
  const formData = new FormData();
  formData.append("file", file);

  const res = await fetch(`${API_BASE}/ingest/data`, {
    method: "POST",
    body: formData,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "Upload failed" }));
    throw new Error(err.detail ?? "Upload failed");
  }
  return res.json();
}

export interface AISuggestion {
  label: string;
  prompt: string;
}

export async function getAISuggestions(): Promise<AISuggestion[]> {
  try {
    const res = await fetch(`${API_BASE}/agent/suggestions`);
    if (!res.ok) return [];
    const data = await res.json();
    return data.suggestions ?? [];
  } catch {
    return [];
  }
}

export async function proposeCellEdit(
  row: number,
  column: string,
  value: string | number,
): Promise<{ diff: { type: "update_cells"; changes: import("./types").CellChange[] } }> {
  const res = await fetch(`${API_BASE}/cells/edit`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ row, column, value }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "Edit failed" }));
    throw new Error(err.detail ?? "Edit failed");
  }
  return res.json();
}

export async function applyDiff(diff: import("./types").Diff): Promise<{ transactions: import("./types").Transaction[] }> {
  const res = await fetch(`${API_BASE}/agent/apply`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ diff }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "Apply failed" }));
    throw new Error(err.detail ?? "Apply failed");
  }
  return res.json();
}

export async function getAuditLog(): Promise<AuditEntry[]> {
  const res = await fetch(`${API_BASE}/audit/log`);
  if (!res.ok) throw new Error("Failed to fetch audit log");
  return res.json();
}
