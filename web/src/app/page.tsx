"use client";

import { useCallback, useRef, useState } from "react";
import SpreadsheetGrid from "@/components/SpreadsheetGrid";
import Sidebar from "@/components/Sidebar";
import { runAgent, uploadFile } from "@/lib/api";
import { SAMPLE_TRANSACTIONS } from "@/lib/sample-data";
import type { Transaction, Diff, CellChange, AuditEntry } from "@/lib/types";

export default function Home() {
  const [transactions, setTransactions] = useState<Transaction[]>(SAMPLE_TRANSACTIONS);
  const [pendingDiff, setPendingDiff] = useState<Diff | null>(null);
  const [pendingTool, setPendingTool] = useState("");
  const [pendingChanges, setPendingChanges] = useState<CellChange[]>([]);
  const [auditLog, setAuditLog] = useState<AuditEntry[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [error, setError] = useState("");

  async function handlePrompt(prompt: string) {
    setError("");
    setIsLoading(true);
    setPendingDiff(null);
    setPendingChanges([]);

    try {
      const res = await runAgent(prompt);
      setPendingDiff(res.diff);
      setPendingTool(res.tool);
      if (res.diff.type === "update_cells") {
        setPendingChanges(res.diff.changes);
      }
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

  const handleAcceptChange = useCallback((change: CellChange) => {
    setTransactions((prev) => {
      const next = prev.map((t) => ({ ...t }));
      (next[change.row] as Record<string, string | number>)[change.column] = change.after;
      return next;
    });
    setPendingChanges((prev) => {
      const next = prev.filter(
        (c) => !(c.row === change.row && c.column === change.column)
      );
      if (next.length === 0) {
        setPendingDiff(null);
        setPendingTool("");
      }
      return next;
    });
  }, []);

  const handleRejectChange = useCallback((change: CellChange) => {
    setPendingChanges((prev) => {
      const next = prev.filter(
        (c) => !(c.row === change.row && c.column === change.column)
      );
      if (next.length === 0) {
        setPendingDiff(null);
        setPendingTool("");
      }
      return next;
    });
  }, []);

  function handleAcceptAll() {
    if (pendingDiff?.type === "update_cells") {
      setTransactions((prev) => {
        const next = prev.map((t) => ({ ...t }));
        for (const change of pendingChanges) {
          (next[change.row] as Record<string, string | number>)[change.column] =
            change.after;
        }
        return next;
      });
    }
    setPendingDiff(null);
    setPendingTool("");
    setPendingChanges([]);
  }

  function handleRejectAll() {
    setPendingDiff(null);
    setPendingTool("");
    setPendingChanges([]);
  }

  const handleCellEdit = useCallback(
    (rowIndex: number, column: string, value: string | number) => {
      setTransactions((prev) => {
        const next = prev.map((t) => ({ ...t }));
        (next[rowIndex] as Record<string, string | number>)[column] = value;
        return next;
      });
    },
    [],
  );

  async function handleFileUpload(file: File) {
    setError("");
    setIsUploading(true);
    try {
      const res = await uploadFile(file);
      setTransactions(res.transactions);
      setPendingDiff(null);
      setPendingChanges([]);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Upload failed");
    } finally {
      setIsUploading(false);
    }
  }

  // --- Resizable sidebar ---
  const [sidebarWidth, setSidebarWidth] = useState(320);
  const isDragging = useRef(false);
  const startX = useRef(0);
  const startWidth = useRef(320);

  function handleMouseDown(e: React.MouseEvent) {
    isDragging.current = true;
    startX.current = e.clientX;
    startWidth.current = sidebarWidth;
    document.body.style.cursor = "col-resize";
    document.body.style.userSelect = "none";

    function onMouseMove(ev: MouseEvent) {
      if (!isDragging.current) return;
      const delta = startX.current - ev.clientX;
      const newWidth = Math.min(Math.max(startWidth.current + delta, 240), 600);
      setSidebarWidth(newWidth);
    }

    function onMouseUp() {
      isDragging.current = false;
      document.body.style.cursor = "";
      document.body.style.userSelect = "";
      document.removeEventListener("mousemove", onMouseMove);
      document.removeEventListener("mouseup", onMouseUp);
    }

    document.addEventListener("mousemove", onMouseMove);
    document.addEventListener("mouseup", onMouseUp);
  }

  return (
    <div className="flex h-screen">
      {/* Spreadsheet Area — full height, no top bar */}
      <div className="flex-1 flex flex-col min-w-0">
        <SpreadsheetGrid
          transactions={transactions}
          pendingChanges={pendingChanges}
          onAcceptChange={handleAcceptChange}
          onRejectChange={handleRejectChange}
          onCellEdit={handleCellEdit}
        />
      </div>

      {/* Resize Handle */}
      <div
        onMouseDown={handleMouseDown}
        className="w-1 cursor-col-resize bg-emerald-900/40 hover:bg-emerald-500 active:bg-emerald-400 transition-colors flex-shrink-0"
      />

      {/* Sidebar */}
      <div
        style={{ width: sidebarWidth }}
        className="border-l border-emerald-900/30 flex-shrink-0 overflow-hidden"
      >
        <Sidebar
          onPrompt={handlePrompt}
          isLoading={isLoading}
          error={error}
          pendingDiff={pendingDiff}
          pendingTool={pendingTool}
          pendingChanges={pendingChanges}
          onAcceptAll={handleAcceptAll}
          onRejectAll={handleRejectAll}
          auditLog={auditLog}
          onFileUpload={handleFileUpload}
          isUploading={isUploading}
        />
      </div>
    </div>
  );
}
