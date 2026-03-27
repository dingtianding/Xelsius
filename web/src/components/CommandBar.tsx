"use client";

import { useState } from "react";

interface CommandBarProps {
  onSubmit: (prompt: string) => void;
  isLoading: boolean;
}

export default function CommandBar({ onSubmit, isLoading }: CommandBarProps) {
  const [input, setInput] = useState("");

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const trimmed = input.trim();
    if (!trimmed || isLoading) return;
    onSubmit(trimmed);
    setInput("");
  }

  return (
    <form onSubmit={handleSubmit} className="flex gap-2">
      <div className="relative flex-1">
        <span className="absolute left-3 top-1/2 -translate-y-1/2 text-zinc-400 text-sm font-mono">
          &gt;
        </span>
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder='Try "categorize all transactions" or "highlight anomalies"'
          disabled={isLoading}
          className="w-full pl-7 pr-4 py-2.5 bg-zinc-900 border border-zinc-700 rounded-lg text-sm text-zinc-100 placeholder:text-zinc-500 focus:outline-none focus:border-emerald-500 focus:ring-1 focus:ring-emerald-500 font-mono disabled:opacity-50"
        />
      </div>
      <button
        type="submit"
        disabled={isLoading || !input.trim()}
        className="px-4 py-2.5 bg-emerald-600 hover:bg-emerald-500 disabled:bg-zinc-700 disabled:text-zinc-500 text-white text-sm font-medium rounded-lg transition-colors"
      >
        {isLoading ? "Running..." : "Run"}
      </button>
    </form>
  );
}
