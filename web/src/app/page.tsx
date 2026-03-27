"use client";

import { useState } from "react";
import CommandBar from "@/components/CommandBar";
import TransactionTable from "@/components/TransactionTable";
import DiffPreview from "@/components/DiffPreview";
import AuditLog from "@/components/AuditLog";
import { runAgent } from "@/lib/api";
import { SAMPLE_TRANSACTIONS } from "@/lib/sample-data";
import type { Transaction, Diff, CellChange, AuditEntry } from "@/lib/types";

export default function Home() {
  const [transactions, setTransactions] = useState<Transaction[]>(SAMPLE_TRANSACTIONS);
  const [pendingDiff, setPendingDiff] = useState<Diff | null>(null);
  const [pendingTool, setPendingTool] = useState("");
  const [auditLog, setAuditLog] = useState<AuditEntry[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState("");

  const pendingChanges: CellChange[] =
    pendingDiff?.type === "update_cells" ? pendingDiff.changes : [];

  async function handlePrompt(prompt: string) {
    setError("");
    setIsLoading(true);
    setPendingDiff(null);

    try {
      const res = await runAgent(prompt);
      setPendingDiff(res.diff);
      setPendingTool(res.tool);
      setAuditLog((prev) => [
        {
          prompt,
          tool: res.tool,
          args: res.args,
          diff: res.diff,
          timestamp: new Date().toISOString(),
        },
        ...prev,
      ]);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Something went wrong");
    } finally {
      setIsLoading(false);
    }
  }

  function handleApply() {
    if (!pendingDiff) return;

    if (pendingDiff.type === "update_cells") {
      setTransactions((prev) => {
        const next = prev.map((t) => ({ ...t }));
        for (const change of pendingDiff.changes) {
          (next[change.row] as Record<string, string | number>)[change.column] =
            change.after;
        }
        return next;
      });
    }

    setPendingDiff(null);
    setPendingTool("");
  }

  function handleReject() {
    setPendingDiff(null);
    setPendingTool("");
  }

  return (
    <main className="max-w-5xl mx-auto px-6 py-10 flex flex-col gap-6">
      <div>
        <h1 className="text-2xl font-bold text-zinc-100 tracking-tight">Xelsius</h1>
        <p className="text-sm text-zinc-400 mt-1">
          Describe what you want to do. Review the diff. Apply when ready.
        </p>
      </div>

      <CommandBar onSubmit={handlePrompt} isLoading={isLoading} />

      {error && (
        <div className="text-sm text-red-400 bg-red-400/10 border border-red-400/20 rounded-lg px-4 py-2.5">
          {error}
        </div>
      )}

      {pendingDiff && (
        <DiffPreview
          diff={pendingDiff}
          tool={pendingTool}
          onApply={handleApply}
          onReject={handleReject}
        />
      )}

      <TransactionTable
        transactions={transactions}
        pendingChanges={pendingChanges}
      />

      <AuditLog entries={auditLog} />
    </main>
  );
}
