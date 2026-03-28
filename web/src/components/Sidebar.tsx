"use client";

import { useRef, useState } from "react";
import type { AuditEntry, CellChange, Diff } from "@/lib/types";

interface ChatMessage {
  role: "user" | "assistant";
  content: string;
  diff?: Diff;
  tool?: string;
  fileName?: string;
}

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
  onFileUpload: (file: File) => void;
  isUploading: boolean;
}

type Mode = "agent" | "chat";

const MODELS = [
  { id: "auto", label: "Auto" },
  { id: "claude-haiku-4-5", label: "Haiku 4.5" },
  { id: "claude-sonnet-4-5", label: "Sonnet 4.5" },
  { id: "claude-opus-4", label: "Opus 4" },
];

const VALID_EXTENSIONS = [".csv", ".xlsx", ".xls"];

function isValidFile(file: File): boolean {
  return VALID_EXTENSIONS.some((ext) => file.name.toLowerCase().endsWith(ext));
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
  onFileUpload,
  isUploading,
}: SidebarProps) {
  const [input, setInput] = useState("");
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [mode, setMode] = useState<Mode>("agent");
  const [model, setModel] = useState("auto");
  const [isDragOver, setIsDragOver] = useState(false);
  const [attachedFile, setAttachedFile] = useState<File | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const changeCount =
    pendingDiff?.type === "update_cells"
      ? pendingChanges.length
      : pendingDiff?.type === "create_sheet"
        ? pendingDiff.data.length
        : 0;

  function handleFileDrop(file: File) {
    if (!isValidFile(file)) return;
    setAttachedFile(file);
  }

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();

    // If there's an attached file, upload it
    if (attachedFile) {
      setMessages((prev) => [
        ...prev,
        { role: "user", content: `Upload ${attachedFile.name}`, fileName: attachedFile.name },
      ]);
      onFileUpload(attachedFile);
      setAttachedFile(null);

      setTimeout(() => {
        setMessages((prev) => [
          ...prev,
          { role: "assistant", content: "Loading file..." },
        ]);
      }, 100);
      return;
    }

    const trimmed = input.trim();
    if (!trimmed || isLoading) return;

    setMessages((prev) => [...prev, { role: "user", content: trimmed }]);
    setInput("");
    onPrompt(trimmed);

    setTimeout(() => {
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: "Running analysis..." },
      ]);
    }, 100);
  }

  // Update last assistant message when diff arrives
  if (
    pendingDiff &&
    messages.length > 0 &&
    messages[messages.length - 1]?.role === "assistant" &&
    !messages[messages.length - 1]?.diff
  ) {
    const toolLabel = pendingTool.replace(/_/g, " ");
    setMessages((prev) => {
      const next = [...prev];
      next[next.length - 1] = {
        role: "assistant",
        content:
          pendingDiff.type === "update_cells"
            ? `I'll ${toolLabel}. This will update ${changeCount} cell${changeCount !== 1 ? "s" : ""}.`
            : `I'll create a new "${pendingDiff.name}" sheet with ${changeCount} row${changeCount !== 1 ? "s" : ""}.`,
        diff: pendingDiff,
        tool: pendingTool,
      };
      return next;
    });
  }

  // Update last assistant message when file upload completes
  if (
    !isUploading &&
    messages.length > 0 &&
    messages[messages.length - 1]?.role === "assistant" &&
    messages[messages.length - 1]?.content === "Loading file..."
  ) {
    setMessages((prev) => {
      const next = [...prev];
      next[next.length - 1] = {
        role: "assistant",
        content: "File loaded into the spreadsheet.",
      };
      return next;
    });
  }

  return (
    <div className="flex flex-col h-full bg-[#0a1f1a]">
      {/* Header */}
      <div className="px-4 py-3 border-b border-emerald-900/50">
        <div className="flex items-center justify-between">
          <h2 className="text-base font-semibold text-white">Xelsius</h2>
          <span className="text-xs text-zinc-400 font-mono">agent</span>
        </div>
      </div>

      {/* Mode + Model selectors */}
      <div className="flex items-center gap-3 px-4 py-2 border-b border-emerald-900/50">
        <div className="flex bg-emerald-900/40 rounded-md p-0.5">
          {(["agent", "chat"] as Mode[]).map((m) => (
            <button
              key={m}
              onClick={() => setMode(m)}
              className={`px-3 py-1 text-xs font-medium rounded transition-colors capitalize ${
                mode === m
                  ? "bg-emerald-700 text-white"
                  : "text-zinc-400 hover:text-zinc-200"
              }`}
            >
              {m}
            </button>
          ))}
        </div>
        <select
          value={model}
          onChange={(e) => setModel(e.target.value)}
          className="bg-emerald-900/40 border border-emerald-800/40 text-zinc-300 text-xs rounded px-2 py-1 focus:outline-none focus:border-emerald-600 cursor-pointer"
        >
          {MODELS.map((m) => (
            <option key={m.id} value={m.id} className="bg-[#0a1f1a]">
              {m.label}
            </option>
          ))}
        </select>
      </div>

      {/* Chat Messages */}
      <div className="flex-1 overflow-y-auto px-4 py-3">
        {messages.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full text-center gap-5">
            <div className="w-full">
              <div className="flex flex-col gap-1.5">
                {[
                  "Categorize all transactions",
                  "Summarize by category",
                  "Highlight transactions over $1000",
                ].map((suggestion) => (
                  <button
                    key={suggestion}
                    onClick={() => setInput(suggestion)}
                    className="text-left text-sm text-zinc-300 hover:text-zinc-200 hover:bg-emerald-900/30 rounded-md px-3 py-2.5 transition-colors border border-emerald-900/30 hover:border-emerald-700/50"
                  >
                    {suggestion}
                  </button>
                ))}
              </div>
            </div>
          </div>
        ) : (
          <div className="flex flex-col gap-3">
            {messages.map((msg, i) => (
              <div key={i}>
                {msg.role === "user" ? (
                  <div className="flex justify-end">
                    <div className="bg-emerald-800/40 border border-emerald-700/30 rounded-lg px-3 py-2 max-w-[85%]">
                      {msg.fileName && (
                        <div className="flex items-center gap-1.5 mb-1 text-xs text-emerald-400">
                          <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                            <path strokeLinecap="round" strokeLinejoin="round" d="M7 21h10a2 2 0 002-2V9.414a1 1 0 00-.293-.707l-5.414-5.414A1 1 0 0012.586 3H7a2 2 0 00-2 2v14a2 2 0 002 2z" />
                          </svg>
                          {msg.fileName}
                        </div>
                      )}
                      <p className="text-sm text-white">{msg.content}</p>
                    </div>
                  </div>
                ) : (
                  <div className="flex justify-start">
                    <div className="bg-[#0d2a22] border border-emerald-900/40 rounded-lg px-3 py-2 max-w-[85%]">
                      <p className="text-sm text-zinc-200">{msg.content}</p>

                      {msg.diff && i === messages.length - 1 && pendingDiff && (
                        <div className="flex gap-2 mt-2 pt-2 border-t border-emerald-900/40">
                          <button
                            onClick={onAcceptAll}
                            className="flex-1 px-2 py-1 text-xs font-medium text-white bg-emerald-600 hover:bg-emerald-500 rounded transition-colors"
                          >
                            Accept
                          </button>
                          <button
                            onClick={onRejectAll}
                            className="flex-1 px-2 py-1 text-xs font-medium text-zinc-200 bg-emerald-900/50 hover:bg-emerald-800/50 border border-emerald-700/40 rounded transition-colors"
                          >
                            Reject
                          </button>
                        </div>
                      )}

                      {msg.diff?.type === "create_sheet" && (
                        <div className="mt-2 max-h-32 overflow-y-auto rounded border border-emerald-900/40">
                          <table className="w-full text-xs">
                            <thead>
                              <tr className="bg-emerald-900/30 text-zinc-400">
                                {Object.keys(msg.diff.data[0] ?? {}).map((key) => (
                                  <th key={key} className="px-2 py-1 text-left font-medium">
                                    {key}
                                  </th>
                                ))}
                              </tr>
                            </thead>
                            <tbody className="divide-y divide-emerald-900/30">
                              {msg.diff.data.map((row, ri) => (
                                <tr key={ri} className="text-zinc-300">
                                  {Object.values(row).map((val, ci) => (
                                    <td key={ci} className="px-2 py-1 font-mono">
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
                  </div>
                )}
              </div>
            ))}

            {(isLoading || isUploading) && (
              <div className="flex justify-start">
                <div className="bg-[#0d2a22] border border-emerald-900/40 rounded-lg px-3 py-2">
                  <div className="flex gap-1">
                    <span className="w-1.5 h-1.5 bg-emerald-500 rounded-full animate-bounce" style={{ animationDelay: "0ms" }} />
                    <span className="w-1.5 h-1.5 bg-emerald-500 rounded-full animate-bounce" style={{ animationDelay: "150ms" }} />
                    <span className="w-1.5 h-1.5 bg-emerald-500 rounded-full animate-bounce" style={{ animationDelay: "300ms" }} />
                  </div>
                </div>
              </div>
            )}
          </div>
        )}

        {error && (
          <div className="mt-3 text-xs text-red-400 bg-red-400/10 border border-red-400/20 rounded-lg px-3 py-2">
            {error}
          </div>
        )}
      </div>

      {/* Chat Input — supports file drag & drop */}
      <div className="px-3 py-3 border-t border-emerald-900/50">
        <form onSubmit={handleSubmit}>
          <div
            onDragOver={(e) => {
              e.preventDefault();
              setIsDragOver(true);
            }}
            onDragLeave={() => setIsDragOver(false)}
            onDrop={(e) => {
              e.preventDefault();
              setIsDragOver(false);
              const file = e.dataTransfer.files[0];
              if (file) handleFileDrop(file);
            }}
            className={`bg-[#0d2a22] border rounded-lg overflow-hidden transition-colors ${
              isDragOver
                ? "border-emerald-500 bg-emerald-900/30"
                : "border-emerald-800/40 focus-within:border-emerald-600"
            }`}
          >
            {/* Attached file preview */}
            {attachedFile && (
              <div className="flex items-center gap-2 px-3 pt-2">
                <div className="flex items-center gap-1.5 bg-emerald-900/40 border border-emerald-800/40 rounded px-2 py-1 text-xs text-emerald-400">
                  <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M7 21h10a2 2 0 002-2V9.414a1 1 0 00-.293-.707l-5.414-5.414A1 1 0 0012.586 3H7a2 2 0 00-2 2v14a2 2 0 002 2z" />
                  </svg>
                  {attachedFile.name}
                  <button
                    type="button"
                    onClick={() => setAttachedFile(null)}
                    className="ml-1 text-zinc-500 hover:text-zinc-300"
                  >
                    &times;
                  </button>
                </div>
              </div>
            )}

            {/* Drag overlay */}
            {isDragOver && (
              <div className="px-3 py-3 text-center">
                <p className="text-sm text-emerald-400">Drop file here</p>
                <p className="text-xs text-zinc-500">.csv, .xlsx, .xls</p>
              </div>
            )}

            {!isDragOver && (
              <>
                <textarea
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter" && !e.shiftKey) {
                      e.preventDefault();
                      handleSubmit(e);
                    }
                  }}
                  placeholder={attachedFile ? "Press Enter to upload, or add a message..." : "Describe an action..."}
                  disabled={isLoading || isUploading}
                  rows={3}
                  className="w-full px-3 pt-2.5 pb-1 bg-transparent text-sm text-white placeholder:text-zinc-500 focus:outline-none resize-none disabled:opacity-50"
                />
                <div className="flex items-center justify-between px-3 pb-2">
                  <div className="flex items-center gap-2">
                    <button
                      type="button"
                      onClick={() => fileInputRef.current?.click()}
                      className="text-zinc-500 hover:text-zinc-300 transition-colors"
                      title="Attach file"
                    >
                      <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                        <path strokeLinecap="round" strokeLinejoin="round" d="M15.172 7l-6.586 6.586a2 2 0 102.828 2.828l6.414-6.586a4 4 0 00-5.656-5.656l-6.415 6.585a6 6 0 108.486 8.486L20.5 13" />
                      </svg>
                    </button>
                    <span className="text-xs text-zinc-500">
                      Enter to send
                    </span>
                  </div>
                  <button
                    type="submit"
                    disabled={(isLoading || isUploading) || (!input.trim() && !attachedFile)}
                    className="px-3 py-1.5 text-sm font-medium text-white bg-emerald-700 hover:bg-emerald-600 disabled:bg-emerald-900/50 disabled:text-zinc-500 rounded transition-colors"
                  >
                    {isLoading || isUploading ? "..." : "Send"}
                  </button>
                </div>
              </>
            )}
          </div>

          <input
            ref={fileInputRef}
            type="file"
            accept=".csv,.xlsx,.xls"
            onChange={(e) => {
              const file = e.target.files?.[0];
              if (file) handleFileDrop(file);
              if (fileInputRef.current) fileInputRef.current.value = "";
            }}
            className="hidden"
          />
        </form>
      </div>
    </div>
  );
}
