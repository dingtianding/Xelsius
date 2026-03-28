"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import type { AuditEntry, CellChange, Diff, Transaction } from "@/lib/types";
import { getSuggestions } from "@/lib/suggestions";
import { getAISuggestions, type AISuggestion } from "@/lib/api";

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
  transactions: Transaction[];
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
  transactions,
}: SidebarProps) {
  const [input, setInput] = useState("");
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [mode, setMode] = useState<Mode>("agent");
  const [model, setModel] = useState("auto");
  const [isDragOver, setIsDragOver] = useState(false);
  const [attachedFile, setAttachedFile] = useState<File | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const feSuggestions = useMemo(() => getSuggestions(transactions), [transactions]);
  const [aiSuggestions, setAiSuggestions] = useState<AISuggestion[]>([]);
  const [aiLoaded, setAiLoaded] = useState(false);

  useEffect(() => {
    setAiLoaded(false);
    const timer = setTimeout(() => {
      getAISuggestions().then((results) => {
        if (results.length > 0) setAiSuggestions(results);
        setAiLoaded(true);
      });
    }, 500);
    return () => clearTimeout(timer);
  }, [transactions]);

  const suggestions = aiLoaded && aiSuggestions.length > 0 ? aiSuggestions : feSuggestions;

  const changeCount =
    pendingDiff?.type === "update_cells"
      ? pendingChanges.length
      : pendingDiff?.type === "create_sheet"
        ? pendingDiff.data.length
        : 0;

  // Scroll to bottom when new messages arrive
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isLoading, isUploading]);

  function handleFileDrop(file: File) {
    if (!isValidFile(file)) return;
    setAttachedFile(file);
  }

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();

    if (attachedFile) {
      setMessages((prev) => [
        ...prev,
        { role: "user", content: `Upload ${attachedFile.name}`, fileName: attachedFile.name },
      ]);
      onFileUpload(attachedFile);
      setAttachedFile(null);
      setTimeout(() => {
        setMessages((prev) => [...prev, { role: "assistant", content: "Loading file..." }]);
      }, 100);
      return;
    }

    const trimmed = input.trim();
    if (!trimmed || isLoading) return;

    setMessages((prev) => [...prev, { role: "user", content: trimmed }]);
    setInput("");
    onPrompt(trimmed);
    setTimeout(() => {
      setMessages((prev) => [...prev, { role: "assistant", content: "Running analysis..." }]);
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

  if (
    !isUploading &&
    messages.length > 0 &&
    messages[messages.length - 1]?.role === "assistant" &&
    messages[messages.length - 1]?.content === "Loading file..."
  ) {
    setMessages((prev) => {
      const next = [...prev];
      next[next.length - 1] = { role: "assistant", content: "File loaded into the spreadsheet." };
      return next;
    });
  }

  return (
    <div className="flex flex-col h-full bg-[#0a1f1a]">
      {/* Header */}
      <div className="px-4 py-2.5 border-b border-emerald-900/50 flex items-center justify-between">
        <span className="text-sm font-medium text-white">Xelsius Chat</span>
        <div className="flex items-center gap-2">
          <button
            onClick={() => setMessages([])}
            className="text-zinc-500 hover:text-zinc-300 text-lg leading-none"
            title="New chat"
          >+</button>
          <button className="text-zinc-500 hover:text-zinc-300 text-xs leading-none">···</button>
        </div>
      </div>

      {/* Messages — column-reverse so latest is at top */}
      <div className="flex-1 overflow-y-auto flex flex-col-reverse">
        <div ref={messagesEndRef} />

        {/* Suggestions at the bottom (visually top in reverse) when no messages */}
        {messages.length === 0 && (
          <div className="px-4 py-4">
            <div className="flex flex-col gap-1.5">
              {suggestions.map((s) => (
                <button
                  key={s.prompt}
                  onClick={() => setInput(s.prompt)}
                  className="text-left text-sm text-zinc-400 hover:text-zinc-200 hover:bg-emerald-900/30 rounded-md px-3 py-2 transition-colors cursor-pointer"
                >
                  {s.label}
                </button>
              ))}
            </div>
          </div>
        )}

        {/* Messages */}
        <div className="flex flex-col gap-0.5 px-4 py-3">
          {messages.map((msg, i) => (
            <div key={i} className="py-2">
              {msg.role === "user" ? (
                <div>
                  {msg.fileName && (
                    <div className="flex items-center gap-1.5 mb-1 text-xs text-emerald-400">
                      <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                        <path strokeLinecap="round" strokeLinejoin="round" d="M7 21h10a2 2 0 002-2V9.414a1 1 0 00-.293-.707l-5.414-5.414A1 1 0 0012.586 3H7a2 2 0 00-2 2v14a2 2 0 002 2z" />
                      </svg>
                      {msg.fileName}
                    </div>
                  )}
                  <p className="text-sm text-white font-medium">{msg.content}</p>
                </div>
              ) : (
                <div className="border-l-2 border-emerald-700/50 pl-3">
                  <p className="text-sm text-zinc-300">{msg.content}</p>

                  {msg.diff && i === messages.length - 1 && pendingDiff && (
                    <div className="flex gap-2 mt-2">
                      <button
                        onClick={onAcceptAll}
                        className="px-3 py-1 text-xs font-medium text-white bg-emerald-600 hover:bg-emerald-500 rounded transition-colors"
                      >
                        Accept
                      </button>
                      <button
                        onClick={onRejectAll}
                        className="px-3 py-1 text-xs font-medium text-zinc-300 hover:text-white transition-colors"
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
                              <th key={key} className="px-2 py-1 text-left font-medium">{key}</th>
                            ))}
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-emerald-900/30">
                          {msg.diff.data.map((row, ri) => (
                            <tr key={ri} className="text-zinc-300">
                              {Object.values(row).map((val, ci) => (
                                <td key={ci} className="px-2 py-1 font-mono">
                                  {typeof val === "number"
                                    ? val.toLocaleString("en-US", { style: "currency", currency: "USD" })
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
              )}
            </div>
          ))}

          {(isLoading || isUploading) && (
            <div className="py-2 border-l-2 border-emerald-700/50 pl-3">
              <div className="flex gap-1">
                <span className="w-1.5 h-1.5 bg-emerald-500 rounded-full animate-bounce" style={{ animationDelay: "0ms" }} />
                <span className="w-1.5 h-1.5 bg-emerald-500 rounded-full animate-bounce" style={{ animationDelay: "150ms" }} />
                <span className="w-1.5 h-1.5 bg-emerald-500 rounded-full animate-bounce" style={{ animationDelay: "300ms" }} />
              </div>
            </div>
          )}
        </div>

        {error && (
          <div className="mx-4 mb-2 text-xs text-red-400 bg-red-400/10 border border-red-400/20 rounded px-3 py-2">
            {error}
          </div>
        )}
      </div>

      {/* Input at bottom */}
      <div className="px-3 py-3 border-t border-emerald-900/50">
        <form onSubmit={handleSubmit}>
          <div
            onDragOver={(e) => { e.preventDefault(); setIsDragOver(true); }}
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
            {attachedFile && (
              <div className="flex items-center gap-2 px-3 pt-2">
                <div className="flex items-center gap-1.5 bg-emerald-900/40 border border-emerald-800/40 rounded px-2 py-1 text-xs text-emerald-400">
                  <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M7 21h10a2 2 0 002-2V9.414a1 1 0 00-.293-.707l-5.414-5.414A1 1 0 0012.586 3H7a2 2 0 00-2 2v14a2 2 0 002 2z" />
                  </svg>
                  {attachedFile.name}
                  <button type="button" onClick={() => setAttachedFile(null)} className="ml-1 text-zinc-500 hover:text-zinc-300">&times;</button>
                </div>
              </div>
            )}

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
                  placeholder={attachedFile ? "Press Enter to upload..." : "Plan, @ for context, / for commands"}
                  disabled={isLoading || isUploading}
                  rows={3}
                  className="w-full px-3 pt-2.5 pb-1 bg-transparent text-sm text-white placeholder:text-zinc-500 focus:outline-none resize-none disabled:opacity-50"
                />
                <div className="flex items-center justify-between px-3 pb-2">
                  <div className="flex items-center gap-2">
                    <div className="flex bg-emerald-900/40 rounded-full p-0.5">
                      {(["agent", "chat"] as Mode[]).map((m) => (
                        <button
                          key={m}
                          type="button"
                          onClick={() => setMode(m)}
                          className={`px-2.5 py-0.5 text-[11px] font-medium rounded-full transition-colors capitalize ${
                            mode === m ? "bg-emerald-700 text-white" : "text-zinc-500 hover:text-zinc-200"
                          }`}
                        >
                          {m}
                        </button>
                      ))}
                    </div>
                    <select
                      value={model}
                      onChange={(e) => setModel(e.target.value)}
                      className="bg-transparent border-none text-zinc-400 text-xs focus:outline-none cursor-pointer"
                    >
                      {MODELS.map((m) => (
                        <option key={m.id} value={m.id} className="bg-[#0a1f1a]">{m.label}</option>
                      ))}
                    </select>
                  </div>
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
                  </div>
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
