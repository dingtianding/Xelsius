export interface Transaction {
  date: string;
  description: string;
  amount: number;
  category: string;
}

export interface CellChange {
  row: number;
  column: string;
  before: string | number;
  after: string | number;
}

export interface UpdateCellsDiff {
  type: "update_cells";
  changes: CellChange[];
}

export interface CreateSheetDiff {
  type: "create_sheet";
  name: string;
  data: Record<string, string | number>[];
}

export type Diff = UpdateCellsDiff | CreateSheetDiff;

export interface RunResponse {
  tool: string;
  args: Record<string, unknown>;
  diff: Diff;
}

export interface UploadResponse {
  transactions: Transaction[];
  count: number;
}

export interface AuditEntry {
  prompt: string;
  tool: string;
  args: Record<string, unknown>;
  diff: Diff;
  timestamp: string;
}
