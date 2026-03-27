"use client";

import type { AuditEntry, CellChange, Diff } from "@/lib/types";
import CommandBar from "./CommandBar";

interface SidebarProps {
  onPrompt: (prompt: string) => void;
  isLoading: boolean;
  error: string;
  pendingDiff: Diff | null;
  pendingTool: string;
  pendingChanges: CellChange[];
  onAcceptAll: () => void;
  onRejectAll: () => void;
  auditLog: AuditEntry[];
}

export default function Sidebar({
  onPrompt,
  isLoading,
  error,
  pendingDiff,
  pendingTool,
  pendingChanges,
  onAcceptAll,
  onRejectAll,
  auditLog,
}: SidebarProps) {
  const changeCount =
    pendingDiff?.type === "update_cells"
      ? pendingChanges.length
      : pendingDiff?.type === "create_sheet"
        ? pendingDiff.data.length
        : 0;

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="px-4 py-4 border-b border-zinc-800">
        <h2 className="text-sm font-semibold text-zinc-100 tracking-tight">
          Xelsius Agent
        </h2>
        <p className="text-xs text-zinc-500 mt-0.5">
          Describe what you want to do
        </p>
      </div>

      {/* Command Input */}
      <div className="px-4 py-3 border-b border-zinc-800">
        <CommandBar onSubmit={onPrompt} isLoading={isLoading} />
      </div>

      {/* Error */}
      {error && (
        <div className="mx-4 mt-3 text-xs text-red-400 bg-red-400/10 border border-red-400/20 rounded px-3 py-2">
          {error}
        </div>
      )}

      {/* Pending Diff */}
      {pendingDiff && changeCount > 0 && (
        <div className="mx-4 mt-3 border border-emerald-500/30 bg-emerald-500/5 rounded-lg p-3">
          <div className="flex items-center justify-between mb-2">
            <div>
              <p className="text-xs font-medium text-emerald-400">
                Proposed Changes
              </p>
              <p className="text-xs text-zinc-500 mt-0.5">
                <span className="font-mono text-zinc-400">{pendingTool}</span>
              </p>
            </div>
          </div>

          <p className="text-xs text-zinc-400 mb-3">
            {pendingDiff.type === "update_cells"
              ? `${changeCount} cell${changeCount !== 1 ? "s" : ""} to update`
              : `New sheet with ${changeCount} rows`}
          </p>

          {/* Summary for create_sheet */}
          {pendingDiff.type === "create_sheet" && (
            <div className="mb-3 max-h-32 overflow-y-auto rounded border border-zinc-700">
              <table className="w-full text-xs">
                <thead>
                  <tr className="bg-zinc-800 text-zinc-400">
                    {Object.keys(pendingDiff.data[0] ?? {}).map((key) => (
                      <th key={key} className="px-2 py-1 text-left font-medium">
                        {key}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody className="divide-y divide-zinc-800">
                  {pendingDiff.data.map((row, i) => (
                    <tr key={i} className="text-zinc-300">
                      {Object.values(row).map((val, j) => (
                        <td key={j} className="px-2 py-1 font-mono">
                          {typeof val === "number"
                            ? val.toLocaleString("en-US", {
                                style: "currency",
                                currency: "USD",
                              })
                            : val}
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          <div className="flex gap-2">
            <button
              onClick={onAcceptAll}
              className="flex-1 px-3 py-1.5 text-xs font-medium text-white bg-emerald-600 hover:bg-emerald-500 rounded transition-colors"
            >
              Accept All
            </button>
            <button
              onClick={onRejectAll}
              className="flex-1 px-3 py-1.5 text-xs font-medium text-zinc-300 bg-zinc-800 hover:bg-zinc-700 border border-zinc-600 rounded transition-colors"
            >
              Reject All
            </button>
          </div>
        </div>
      )}

      {/* Suggestions */}
      {!pendingDiff && !isLoading && (
        <div className="mx-4 mt-3">
          <p className="text-xs text-zinc-500 mb-2">Try:</p>
          <div className="flex flex-col gap-1.5">
            {[
              "Categorize all transactions",
              "Summarize by category",
              "Highlight transactions over $1000",
            ].map((suggestion) => (
              <button
                key={suggestion}
                onClick={() => onPrompt(suggestion)}
                className="text-left text-xs text-zinc-400 hover:text-zinc-200 hover:bg-zinc-800 rounded px-2 py-1.5 transition-colors font-mono"
              >
                &gt; {suggestion}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Audit Log */}
      <div className="flex-1 mt-4 overflow-hidden flex flex-col">
        <div className="px-4 py-2 border-t border-zinc-800">
          <h3 className="text-xs font-medium text-zinc-500 uppercase tracking-wider">
            History
          </h3>
        </div>
        <div className="flex-1 overflow-y-auto px-4">
          {auditLog.length === 0 ? (
            <p className="text-xs text-zinc-600 italic py-2">No actions yet</p>
          ) : (
            <div className="flex flex-col gap-1 pb-4">
              {auditLog.map((entry, i) => (
                <div
                  key={i}
                  className="text-xs py-1.5 border-b border-zinc-800/50"
                >
                  <p className="text-zinc-300 truncate">&quot;{entry.prompt}&quot;</p>
                  <div className="flex items-center gap-2 mt-0.5">
                    <span className="text-emerald-500 font-mono">{entry.tool}</span>
                    <span className="text-zinc-600">
                      {new Date(entry.timestamp).toLocaleTimeString()}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
