"use client";

import type { Diff } from "@/lib/types";

interface DiffPreviewProps {
  diff: Diff;
  tool: string;
  onApply: () => void;
  onReject: () => void;
}

export default function DiffPreview({ diff, tool, onApply, onReject }: DiffPreviewProps) {
  const changeCount =
    diff.type === "update_cells" ? diff.changes.length : diff.data.length;

  return (
    <div className="border border-emerald-500/30 bg-emerald-500/5 rounded-lg p-4">
      <div className="flex items-center justify-between mb-3">
        <div>
          <h3 className="text-sm font-medium text-emerald-400">Proposed Changes</h3>
          <p className="text-xs text-zinc-400 mt-0.5">
            <span className="font-mono text-zinc-300">{tool}</span>
            {" — "}
            {diff.type === "update_cells"
              ? `${changeCount} cell${changeCount !== 1 ? "s" : ""} to update`
              : `New sheet "${diff.name}" with ${changeCount} row${changeCount !== 1 ? "s" : ""}`}
          </p>
        </div>
        <div className="flex gap-2">
          <button
            onClick={onReject}
            className="px-3 py-1.5 text-xs font-medium text-zinc-300 bg-zinc-800 hover:bg-zinc-700 border border-zinc-600 rounded-md transition-colors"
          >
            Reject
          </button>
          <button
            onClick={onApply}
            className="px-3 py-1.5 text-xs font-medium text-white bg-emerald-600 hover:bg-emerald-500 rounded-md transition-colors"
          >
            Apply
          </button>
        </div>
      </div>

      {diff.type === "create_sheet" && (
        <div className="overflow-x-auto rounded border border-zinc-700 mt-2">
          <table className="w-full text-xs">
            <thead>
              <tr className="bg-zinc-800 text-zinc-400">
                {Object.keys(diff.data[0] ?? {}).map((key) => (
                  <th key={key} className="px-3 py-2 text-left font-medium">
                    {key}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-zinc-800">
              {diff.data.map((row, i) => (
                <tr key={i} className="text-zinc-200">
                  {Object.values(row).map((val, j) => (
                    <td key={j} className="px-3 py-1.5 font-mono">
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
    </div>
  );
}
