"use client";

import type { AuditEntry } from "@/lib/types";

interface AuditLogProps {
  entries: AuditEntry[];
}

export default function AuditLog({ entries }: AuditLogProps) {
  if (entries.length === 0) return null;

  return (
    <div className="border border-zinc-700 rounded-lg overflow-hidden">
      <div className="bg-zinc-800 px-4 py-2.5 border-b border-zinc-700">
        <h3 className="text-sm font-medium text-zinc-300">Audit Log</h3>
      </div>
      <div className="divide-y divide-zinc-800 max-h-48 overflow-y-auto">
        {entries.map((entry, i) => (
          <div key={i} className="px-4 py-2.5 flex items-center gap-4 text-xs">
            <span className="text-zinc-500 font-mono shrink-0">
              {new Date(entry.timestamp).toLocaleTimeString()}
            </span>
            <span className="text-zinc-200 truncate">
              &quot;{entry.prompt}&quot;
            </span>
            <span className="text-emerald-400 font-mono shrink-0">
              {entry.tool}
            </span>
            <span className="text-zinc-500 shrink-0">
              {entry.diff.type === "update_cells"
                ? `${entry.diff.changes.length} changes`
                : `new sheet`}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}
