"use client";

import { useEffect, useRef, useCallback } from "react";
import { UniverSheetsCorePreset } from "@univerjs/preset-sheets-core";
import sheetsCoreEnUS from "@univerjs/preset-sheets-core/locales/en-US";
import { createUniver, LocaleType, mergeLocales } from "@univerjs/presets";
import type { FUniver } from "@univerjs/presets";

import "@univerjs/preset-sheets-core/lib/index.css";

import type { Transaction, CellChange } from "@/lib/types";

interface SpreadsheetGridProps {
  transactions: Transaction[];
  pendingChanges: CellChange[];
  onAcceptChange: (change: CellChange) => void;
  onRejectChange: (change: CellChange) => void;
  onCellEdit: (rowIndex: number, column: string, value: string | number) => void;
}

const COL_MAP: Record<string, number> = {
  date: 0,
  description: 1,
  amount: 2,
  category: 3,
};

const COL_REVERSE: Record<number, string> = {
  0: "date",
  1: "description",
  2: "amount",
  3: "category",
};

function buildWorkbookData(transactions: Transaction[]) {
  const cellData: Record<number, Record<number, { v: string | number }>> = {};

  // Header row
  cellData[0] = {
    0: { v: "Date" },
    1: { v: "Description" },
    2: { v: "Amount" },
    3: { v: "Category" },
  };

  // Data rows
  transactions.forEach((txn, i) => {
    cellData[i + 1] = {
      0: { v: txn.date },
      1: { v: txn.description },
      2: { v: txn.amount },
      3: { v: txn.category || "" },
    };
  });

  return {
    id: "xelsius-workbook",
    sheetOrder: ["transactions"],
    name: "Xelsius",
    appVersion: "1.0.0",
    sheets: {
      transactions: {
        id: "transactions",
        name: "Transactions",
        rowCount: transactions.length + 5,
        columnCount: 6,
        defaultRowHeight: 28,
        defaultColumnWidth: 150,
        columnData: {
          0: { w: 110 },
          1: { w: 250 },
          2: { w: 120 },
          3: { w: 160 },
        },
        cellData,
      },
    },
  };
}

export default function SpreadsheetGrid({
  transactions,
  pendingChanges,
  onAcceptChange,
  onRejectChange,
  onCellEdit,
}: SpreadsheetGridProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const apiRef = useRef<FUniver | null>(null);
  const pendingRef = useRef<CellChange[]>(pendingChanges);
  const onAcceptRef = useRef(onAcceptChange);
  const onRejectRef = useRef(onRejectChange);
  const onCellEditRef = useRef(onCellEdit);
  const transactionsRef = useRef(transactions);

  // Keep refs current
  pendingRef.current = pendingChanges;
  onAcceptRef.current = onAcceptChange;
  onRejectRef.current = onRejectChange;
  onCellEditRef.current = onCellEdit;
  transactionsRef.current = transactions;

  // Initialize Univer once
  useEffect(() => {
    if (!containerRef.current) return;

    const { univerAPI } = createUniver({
      locale: LocaleType.EN_US,
      locales: {
        [LocaleType.EN_US]: mergeLocales(sheetsCoreEnUS),
      },
      presets: [
        UniverSheetsCorePreset({
          container: containerRef.current,
        }),
      ],
    });

    apiRef.current = univerAPI;

    const workbookData = buildWorkbookData(transactionsRef.current);
    univerAPI.createWorkbook(workbookData);

    // Style header row
    const sheet = univerAPI.getActiveWorkbook()?.getActiveSheet();
    if (sheet) {
      sheet.getRange(0, 0, 1, 4)?.setBackgroundColor("#18181b");
      sheet.getRange(0, 0, 1, 4)?.setFontWeight("bold");
      sheet.getRange(0, 0, 1, 4)?.setFontColor("#a1a1aa");
    }

    // Listen for cell edits
    const sub = univerAPI.onCommandExecuted((command) => {
      if (command.id === "sheet.mutation.set-range-values") {
        const sheet = univerAPI.getActiveWorkbook()?.getActiveSheet();
        if (!sheet) return;

        const params = command.params as {
          cellValue?: Record<number, Record<number, { v?: string | number }>>;
        };
        if (!params?.cellValue) return;

        for (const [rowStr, cols] of Object.entries(params.cellValue)) {
          const row = Number(rowStr);
          if (row === 0) continue; // skip header
          for (const [colStr, cell] of Object.entries(cols)) {
            const col = Number(colStr);
            const field = COL_REVERSE[col];
            if (field && cell?.v !== undefined) {
              onCellEditRef.current(row - 1, field, cell.v);
            }
          }
        }
      }
    });

    return () => {
      sub?.dispose();
      univerAPI.dispose();
      apiRef.current = null;
    };
  }, []);

  // Apply diff highlighting
  const applyDiffHighlighting = useCallback(() => {
    const api = apiRef.current;
    if (!api) return;
    const sheet = api.getActiveWorkbook()?.getActiveSheet();
    if (!sheet) return;

    const rowCount = transactionsRef.current.length;

    // Clear previous highlighting on data rows
    for (let r = 1; r <= rowCount; r++) {
      sheet.getRange(r, 0, 1, 4)?.setBackgroundColor("#000000");
      sheet.getRange(r, 0, 1, 4)?.setFontColor("#e4e4e7");
    }

    // Apply pending change highlighting
    for (const change of pendingRef.current) {
      const row = change.row + 1; // offset for header
      const col = COL_MAP[change.column];
      if (col === undefined) continue;

      const range = sheet.getRange(row, col, 1, 1);
      if (!range) continue;

      // Show proposed value in the cell
      range.setValue(change.after);
      range.setBackgroundColor("#064e3b");
      range.setFontColor("#6ee7b7");
    }
  }, []);

  // Sync transactions to sheet when they change (after accept)
  useEffect(() => {
    const api = apiRef.current;
    if (!api) return;
    const sheet = api.getActiveWorkbook()?.getActiveSheet();
    if (!sheet) return;

    transactions.forEach((txn, i) => {
      const row = i + 1;
      sheet.getRange(row, 0, 1, 1)?.setValue(txn.date);
      sheet.getRange(row, 1, 1, 1)?.setValue(txn.description);
      sheet.getRange(row, 2, 1, 1)?.setValue(txn.amount);
      sheet.getRange(row, 3, 1, 1)?.setValue(txn.category || "");
    });

    applyDiffHighlighting();
  }, [transactions, applyDiffHighlighting]);

  // Update highlighting when pending changes change
  useEffect(() => {
    applyDiffHighlighting();
  }, [pendingChanges, applyDiffHighlighting]);

  return (
    <div className="flex flex-col h-full">
      {/* Diff action bar */}
      {pendingChanges.length > 0 && (
        <div className="flex items-center gap-2 px-3 py-2 bg-emerald-950/50 border-b border-emerald-500/30 text-xs">
          <span className="text-emerald-400 font-medium">
            {pendingChanges.length} proposed change{pendingChanges.length !== 1 ? "s" : ""}
          </span>
          <span className="text-zinc-500">|</span>
          <button
            onClick={() => pendingChanges.forEach((c) => onAcceptChange(c))}
            className="text-emerald-400 hover:text-emerald-300 font-medium"
          >
            Accept All (&#x2713;)
          </button>
          <button
            onClick={() => pendingChanges.forEach((c) => onRejectChange(c))}
            className="text-red-400 hover:text-red-300 font-medium"
          >
            Reject All (&#x2717;)
          </button>
        </div>
      )}
      <div ref={containerRef} className="flex-1" />
    </div>
  );
}
