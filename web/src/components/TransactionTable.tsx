"use client";

import type { Transaction, CellChange } from "@/lib/types";

interface TransactionTableProps {
  transactions: Transaction[];
  pendingChanges: CellChange[];
}

const COLUMNS: { key: keyof Transaction; label: string }[] = [
  { key: "date", label: "Date" },
  { key: "description", label: "Description" },
  { key: "amount", label: "Amount" },
  { key: "category", label: "Category" },
];

export default function TransactionTable({
  transactions,
  pendingChanges,
}: TransactionTableProps) {
  function getPendingChange(row: number, column: string): CellChange | undefined {
    return pendingChanges.find((c) => c.row === row && c.column === column);
  }

  function formatAmount(val: number): string {
    return val.toLocaleString("en-US", { style: "currency", currency: "USD" });
  }

  return (
    <div className="overflow-x-auto rounded-lg border border-zinc-700">
      <table className="w-full text-sm">
        <thead>
          <tr className="bg-zinc-800 text-zinc-300 text-left">
            <th className="px-4 py-2.5 font-medium text-zinc-500 w-10">#</th>
            {COLUMNS.map((col) => (
              <th key={col.key} className="px-4 py-2.5 font-medium">
                {col.label}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-zinc-800">
          {transactions.map((txn, idx) => (
            <tr key={idx} className="hover:bg-zinc-800/50 transition-colors">
              <td className="px-4 py-2.5 text-zinc-500 font-mono text-xs">
                {idx + 1}
              </td>
              {COLUMNS.map((col) => {
                const change = getPendingChange(idx, col.key);
                const rawValue = txn[col.key];
                const display =
                  col.key === "amount" ? formatAmount(rawValue as number) : rawValue;

                if (change) {
                  return (
                    <td key={col.key} className="px-4 py-2.5">
                      <div className="flex items-center gap-2">
                        {change.before !== "" && (
                          <span className="line-through text-red-400/70 text-xs">
                            {change.before}
                          </span>
                        )}
                        <span className="text-emerald-400 font-medium bg-emerald-400/10 px-1.5 py-0.5 rounded">
                          {change.after}
                        </span>
                      </div>
                    </td>
                  );
                }

                return (
                  <td
                    key={col.key}
                    className={`px-4 py-2.5 ${
                      col.key === "amount" ? "font-mono" : ""
                    } ${col.key === "category" && !rawValue ? "text-zinc-600 italic" : "text-zinc-200"}`}
                  >
                    {display || "—"}
                  </td>
                );
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
