"use client";

import { useEffect, useRef, useState } from "react";
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

function buildCellData(transactions: Transaction[]) {
  const cellData: Record<number, Record<number, { v: string | number; s?: string }>> = {};

  cellData[0] = {
    0: { v: "Date" },
    1: { v: "Description" },
    2: { v: "Amount" },
    3: { v: "Category" },
  };

  transactions.forEach((txn, i) => {
    cellData[i + 1] = {
      0: { v: txn.date },
      1: { v: txn.description },
      2: { v: txn.amount },
      3: { v: txn.category || "" },
    };
  });

  return cellData;
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
  const isUpdatingRef = useRef(false);
  const onCellEditRef = useRef(onCellEdit);
  onCellEditRef.current = onCellEdit;

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

    univerAPI.createWorkbook({
      id: "xelsius-workbook",
      sheetOrder: ["transactions"],
      name: "Xelsius",
      appVersion: "1.0.0",
      sheets: {
        transactions: {
          id: "transactions",
          name: "Transactions",
          rowCount: 50,
          columnCount: 6,
          defaultRowHeight: 28,
          defaultColumnWidth: 150,
          columnData: {
            0: { w: 110 },
            1: { w: 250 },
            2: { w: 120 },
            3: { w: 160 },
          },
          cellData: buildCellData(transactions),
        },
      },
    });

    // Style header
    const sheet = univerAPI.getActiveWorkbook()?.getActiveSheet();
    if (sheet) {
      const headerRange = sheet.getRange(0, 0, 1, 4);
      headerRange?.setBackgroundColor("#18181b");
      headerRange?.setFontWeight("bold");
      headerRange?.setFontColor("#a1a1aa");
    }

    // Listen for user edits (not our programmatic updates)
    const sub = univerAPI.onCommandExecuted((command) => {
      if (isUpdatingRef.current) return;
      if (command.id !== "sheet.mutation.set-range-values") return;

      const params = command.params as {
        cellValue?: Record<number, Record<number, { v?: string | number }>>;
      };
      if (!params?.cellValue) return;

      for (const [rowStr, cols] of Object.entries(params.cellValue)) {
        const row = Number(rowStr);
        if (row === 0) continue;
        for (const [colStr, cell] of Object.entries(cols)) {
          const col = Number(colStr);
          const field = COL_REVERSE[col];
          if (field && cell?.v !== undefined) {
            onCellEditRef.current(row - 1, field, cell.v);
          }
        }
      }
    });

    return () => {
      sub?.dispose();
      univerAPI.dispose();
      apiRef.current = null;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Sync data + diff highlighting in a single batch
  useEffect(() => {
    const api = apiRef.current;
    if (!api) return;
    const sheet = api.getActiveWorkbook()?.getActiveSheet();
    if (!sheet) return;

    isUpdatingRef.current = true;

    // Build a set of pending changes for quick lookup
    const changeMap = new Map<string, CellChange>();
    for (const c of pendingChanges) {
      changeMap.set(`${c.row}:${c.column}`, c);
    }

    // Update all data rows in one pass
    for (let i = 0; i < transactions.length; i++) {
      const txn = transactions[i];
      const row = i + 1;
      const values: [string, string | number][] = [
        ["date", txn.date],
        ["description", txn.description],
        ["amount", txn.amount],
        ["category", txn.category || ""],
      ];

      for (const [field, value] of values) {
        const col = COL_MAP[field];
        const range = sheet.getRange(row, col, 1, 1);
        if (!range) continue;

        const change = changeMap.get(`${i}:${field}`);
        if (change) {
          range.setValue(change.after);
          range.setBackgroundColor("#854d0e");
          range.setFontColor("#fef08a");
        } else {
          range.setValue(value);
          range.setBackgroundColor("#000000");
          range.setFontColor("#e4e4e7");
        }
      }
    }

    isUpdatingRef.current = false;
  }, [transactions, pendingChanges]);

  // Position the floating popup near the first changed cell
  const [popupPos, setPopupPos] = useState<{ top: number; left: number } | null>(null);

  useEffect(() => {
    if (pendingChanges.length === 0 || !containerRef.current) {
      setPopupPos(null);
      return;
    }

    // Find the first changed cell's position in the DOM
    const firstChange = pendingChanges[0];
    const row = firstChange.row + 1; // header offset
    const col = COL_MAP[firstChange.column] ?? 0;

    // Small delay to let Univer render
    const timer = setTimeout(() => {
      const api = apiRef.current;
      if (!api || !containerRef.current) return;

      // Find cell element by looking at Univer's canvas container
      const container = containerRef.current;
      const rect = container.getBoundingClientRect();

      // Estimate cell position based on row/col
      // Header height ~28px, each row ~28px, row header ~46px
      const cellTop = 64 + row * 28;
      const cellLeft = 46 + col * 150;

      setPopupPos({
        top: Math.min(cellTop + 32, rect.height - 60),
        left: Math.min(cellLeft, rect.width - 280),
      });
    }, 200);

    return () => clearTimeout(timer);
  }, [pendingChanges]);

  return (
    <div className="relative flex flex-col h-full">
      <div ref={containerRef} className="flex-1" />

      {/* Floating accept/reject popup near changed cells */}
      {pendingChanges.length > 0 && popupPos && (
        <div
          className="absolute z-50 animate-in fade-in"
          style={{ top: popupPos.top, left: popupPos.left }}
        >
          <div className="flex items-center gap-1.5 bg-[#1c1208] border border-amber-500/50 rounded-lg shadow-xl shadow-black/50 px-2.5 py-1.5">
            <span className="text-xs text-amber-400 font-medium mr-1">
              {pendingChanges.length} change{pendingChanges.length !== 1 ? "s" : ""}
            </span>
            <button
              onClick={() => pendingChanges.forEach((c) => onAcceptChange(c))}
              className="flex items-center gap-1 px-2.5 py-1 text-xs font-medium text-white bg-emerald-600 hover:bg-emerald-500 rounded transition-colors"
            >
              <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
              </svg>
              Accept
            </button>
            <button
              onClick={() => pendingChanges.forEach((c) => onRejectChange(c))}
              className="flex items-center gap-1 px-2.5 py-1 text-xs font-medium text-zinc-300 bg-zinc-800 hover:bg-zinc-700 border border-zinc-600 rounded transition-colors"
            >
              <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
              </svg>
              Reject
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
