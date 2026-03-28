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
  const [mode, setMode] = useState<Mode>("agent");
  const [model, setModel] = useState("auto");
  const [isDragOver, setIsDragOver] = useState(false);
  const [attachedFile, setAttachedFile] = useState<File | null>(null);
  const [askBeforeEdits, setAskBeforeEdits] = useState(true);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Tab system
  interface ChatTab {
    id: string;
    name: string;
    messages: ChatMessage[];
  }

  const [tabs, setTabs] = useState<ChatTab[]>([
    { id: "1", name: "New Chat", messages: [] },
  ]);
  const [activeTabId, setActiveTabId] = useState("1");
  const nextTabId = useRef(2);

  const activeTab = tabs.find((t) => t.id === activeTabId) ?? tabs[0];
  const messages = activeTab.messages;

  function setMessages(updater: ChatMessage[] | ((prev: ChatMessage[]) => ChatMessage[])) {
    setTabs((prev) =>
      prev.map((t) => {
        if (t.id !== activeTabId) return t;
        const newMessages = typeof updater === "function" ? updater(t.messages) : updater;
        const name = t.name === "New Chat" && newMessages.length > 0
          ? (newMessages.find((m) => m.role === "user")?.content.slice(0, 20) ?? "New Chat")
          : t.name;
        return { ...t, messages: newMessages, name };
      })
    );
  }

  function addTab() {
    const id = String(nextTabId.current++);
    setTabs((prev) => [...prev, { id, name: "New Chat", messages: [] }]);
    setActiveTabId(id);
  }

  function closeTab(id: string) {
    setTabs((prev) => {
      const next = prev.filter((t) => t.id !== id);
      if (next.length === 0) {
        const newId = String(nextTabId.current++);
        setActiveTabId(newId);
        return [{ id: newId, name: "New Chat", messages: [] }];
      }
      if (activeTabId === id) {
        setActiveTabId(next[0].id);
      }
      return next;
    });
  }

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
      {/* Tab bar */}
      <div className="flex items-center border-b border-emerald-900/50 overflow-x-auto">
        <div className="flex items-center flex-1 min-w-0">
          {tabs.map((tab) => (
            <div
              key={tab.id}
              onClick={() => setActiveTabId(tab.id)}
              className={`flex items-center gap-1 px-3 py-2 text-xs cursor-pointer shrink-0 border-r border-emerald-900/30 ${
                tab.id === activeTabId
                  ? "text-white bg-emerald-900/20"
                  : "text-zinc-500 hover:text-zinc-300"
              }`}
            >
              <span className="truncate max-w-[100px]">{tab.name}</span>
              {tabs.length > 1 && (
                <button
                  onClick={(e) => { e.stopPropagation(); closeTab(tab.id); }}
                  className="text-zinc-600 hover:text-zinc-300 ml-0.5"
                >&times;</button>
              )}
            </div>
          ))}
        </div>
        <div className="flex items-center gap-1.5 px-2 shrink-0">
          <button onClick={addTab} className="text-zinc-500 hover:text-zinc-300 text-sm" title="New chat">+</button>
          <button className="text-zinc-500 hover:text-zinc-300 text-xs">···</button>
        </div>
      </div>

      {/* Model selector row — Claude in Excel style */}
      <div className="flex items-center justify-between px-4 py-2 border-b border-emerald-900/50">
        <div className="flex items-center gap-2">
          <select
            value={model}
            onChange={(e) => setModel(e.target.value)}
            className="bg-emerald-900/40 border border-emerald-700/40 text-white text-xs font-medium rounded-full px-3 py-1 focus:outline-none cursor-pointer"
          >
            {MODELS.map((m) => (
              <option key={m.id} value={m.id} className="bg-[#0a1f1a]">{m.label}</option>
            ))}
          </select>
          <span className="text-[10px] text-emerald-600 font-medium uppercase tracking-wider">Beta</span>
        </div>
        <div className="flex items-center gap-2">
          <button className="text-zinc-500 hover:text-zinc-300" title="History">
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          </button>
          <button className="text-zinc-500 hover:text-zinc-300" title="Settings">
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.066 2.573c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.573 1.066c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.066-2.573c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
              <path strokeLinecap="round" strokeLinejoin="round" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
            </svg>
          </button>
        </div>
      </div>

      {/* Messages area */}
      <div className="flex-1 overflow-y-auto flex flex-col-reverse">
        <div ref={messagesEndRef} />

        {/* Empty state — centered suggestions like Claude in Excel */}
        {messages.length === 0 && (
          <div className="flex-1 flex flex-col items-center justify-center px-6">
            <p className="text-sm text-zinc-500 mb-6">Take actions in your workpaper</p>
            <div className="flex flex-col items-center gap-2.5 w-full max-w-[220px]">
              {suggestions.map((s) => (
                <button
                  key={s.prompt}
                  onClick={() => setInput(s.prompt)}
                  className="w-full text-sm text-zinc-300 hover:text-white border border-emerald-800/40 hover:border-emerald-600 rounded-full px-4 py-2 transition-colors cursor-pointer text-center"
                >
                  {s.label}
                </button>
              ))}
            </div>
          </div>
        )}

        {/* Messages */}
        {messages.length > 0 && (
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
        )}

        {error && (
          <div className="mx-4 mb-2 text-xs text-red-400 bg-red-400/10 border border-red-400/20 rounded px-3 py-2">
            {error}
          </div>
        )}
      </div>

      {/* Input — Claude in Excel style */}
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
            className={`bg-[#0d2a22] border rounded-xl overflow-hidden transition-colors ${
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
                  placeholder="What can I do for you?"
                  disabled={isLoading || isUploading}
                  rows={2}
                  className="w-full px-3 pt-2.5 pb-1 bg-transparent text-sm text-white placeholder:text-zinc-500 focus:outline-none resize-none disabled:opacity-50"
                />
                <div className="flex items-center justify-between px-3 pb-2">
                  <div className="flex items-center gap-2">
                    {/* Ask before edits toggle */}
                    <button
                      type="button"
                      onClick={() => setAskBeforeEdits(!askBeforeEdits)}
                      className={`flex items-center gap-1 text-[11px] rounded-full px-2 py-0.5 transition-colors ${
                        askBeforeEdits
                          ? "text-emerald-400 bg-emerald-900/40"
                          : "text-zinc-500"
                      }`}
                    >
                      <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                        <path strokeLinecap="round" strokeLinejoin="round" d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
                      </svg>
                      Ask before edits
                    </button>
                  </div>

                  <div className="flex items-center gap-1.5">
                    {/* Attach file */}
                    <button
                      type="button"
                      onClick={() => fileInputRef.current?.click()}
                      className="w-7 h-7 flex items-center justify-center rounded-full text-zinc-500 hover:text-zinc-300 hover:bg-emerald-900/30 transition-colors"
                      title="Attach file"
                    >
                      +
                    </button>
                    {/* Send */}
                    <button
                      type="submit"
                      disabled={(isLoading || isUploading) || (!input.trim() && !attachedFile)}
                      className="w-7 h-7 flex items-center justify-center rounded-full bg-emerald-600 hover:bg-emerald-500 disabled:bg-emerald-900/50 disabled:text-zinc-600 text-white transition-colors"
                    >
                      <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
                        <path strokeLinecap="round" strokeLinejoin="round" d="M5 10l7-7m0 0l7 7m-7-7v18" />
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
