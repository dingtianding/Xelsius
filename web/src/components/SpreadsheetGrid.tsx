"use client";

import { useMemo } from "react";
import { AgGridReact } from "ag-grid-react";
import {
  AllCommunityModule,
  ModuleRegistry,
  type ColDef,
  type CellClassRules,
  type ICellRendererParams,
} from "ag-grid-community";
import type { Transaction, CellChange } from "@/lib/types";

ModuleRegistry.registerModules([AllCommunityModule]);

interface SpreadsheetGridProps {
  transactions: Transaction[];
  pendingChanges: CellChange[];
  onAcceptChange: (change: CellChange) => void;
  onRejectChange: (change: CellChange) => void;
}

function DiffCellRenderer(props: ICellRendererParams) {
  const change: CellChange | undefined = props.data?._changes?.[props.colDef?.field ?? ""];

  if (!change) {
    const val = props.value;
    if (props.colDef?.field === "amount" && typeof val === "number") {
      return <span>{val.toLocaleString("en-US", { style: "currency", currency: "USD" })}</span>;
    }
    if (props.colDef?.field === "category" && !val) {
      return <span className="text-zinc-600 italic">—</span>;
    }
    return <span>{val}</span>;
  }

  const onAccept = props.data?._onAccept;
  const onReject = props.data?._onReject;

  return (
    <div className="flex items-center gap-1.5 w-full group">
      <div className="flex items-center gap-1.5 flex-1 min-w-0">
        {change.before !== "" && (
          <span className="line-through text-red-400/60 text-xs shrink-0">
            {change.before}
          </span>
        )}
        <span className="text-emerald-300 font-medium truncate">{change.after}</span>
      </div>
      <div className="flex gap-0.5 shrink-0 opacity-0 group-hover:opacity-100 transition-opacity">
        <button
          onClick={(e) => {
            e.stopPropagation();
            onAccept?.(change);
          }}
          className="w-5 h-5 flex items-center justify-center rounded text-emerald-400 hover:bg-emerald-400/20 text-xs"
          title="Accept"
        >
          &#x2713;
        </button>
        <button
          onClick={(e) => {
            e.stopPropagation();
            onReject?.(change);
          }}
          className="w-5 h-5 flex items-center justify-center rounded text-red-400 hover:bg-red-400/20 text-xs"
          title="Reject"
        >
          &#x2717;
        </button>
      </div>
    </div>
  );
}

export default function SpreadsheetGrid({
  transactions,
  pendingChanges,
  onAcceptChange,
  onRejectChange,
}: SpreadsheetGridProps) {
  const changeMap = useMemo(() => {
    const map = new Map<number, Map<string, CellChange>>();
    for (const c of pendingChanges) {
      if (!map.has(c.row)) map.set(c.row, new Map());
      map.get(c.row)!.set(c.column, c);
    }
    return map;
  }, [pendingChanges]);

  const rowData = useMemo(() => {
    return transactions.map((txn, idx) => {
      const rowChanges = changeMap.get(idx);
      const changes: Record<string, CellChange> = {};
      if (rowChanges) {
        for (const [col, change] of rowChanges) {
          changes[col] = change;
        }
      }
      return {
        _rowIndex: idx,
        _changes: changes,
        _onAccept: onAcceptChange,
        _onReject: onRejectChange,
        ...txn,
      };
    });
  }, [transactions, changeMap, onAcceptChange, onRejectChange]);

  const diffCellClassRules: CellClassRules = {
    "bg-emerald-500/10 border-l-2 border-l-emerald-500": (params) => {
      const field = params.colDef?.field ?? "";
      return !!params.data?._changes?.[field];
    },
  };

  const columnDefs: ColDef[] = useMemo(
    () => [
      {
        headerName: "#",
        valueGetter: (params) => (params.data?._rowIndex ?? 0) + 1,
        width: 50,
        pinned: "left" as const,
        cellClass: "text-zinc-500 font-mono text-xs",
        sortable: false,
        filter: false,
      },
      {
        field: "date",
        headerName: "Date",
        width: 120,
        cellRenderer: DiffCellRenderer,
        cellClassRules: diffCellClassRules,
      },
      {
        field: "description",
        headerName: "Description",
        flex: 2,
        minWidth: 200,
        cellRenderer: DiffCellRenderer,
        cellClassRules: diffCellClassRules,
      },
      {
        field: "amount",
        headerName: "Amount",
        width: 130,
        cellRenderer: DiffCellRenderer,
        cellClassRules: diffCellClassRules,
      },
      {
        field: "category",
        headerName: "Category",
        flex: 1,
        minWidth: 160,
        cellRenderer: DiffCellRenderer,
        cellClassRules: diffCellClassRules,
      },
    ],
    [diffCellClassRules],
  );

  return (
    <div className="ag-theme-alpine-dark w-full h-full rounded-lg overflow-hidden border border-zinc-700">
      <AgGridReact
        rowData={rowData}
        columnDefs={columnDefs}
        headerHeight={36}
        rowHeight={40}
        domLayout="autoHeight"
        suppressCellFocus={true}
        suppressRowHoverHighlight={false}
      />
    </div>
  );
}
