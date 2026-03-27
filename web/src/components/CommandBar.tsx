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
    <form onSubmit={handleSubmit} className="flex flex-col gap-2">
      <div className="relative">
        <span className="absolute left-2.5 top-1/2 -translate-y-1/2 text-zinc-500 text-xs font-mono">
          &gt;
        </span>
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Describe an action..."
          disabled={isLoading}
          className="w-full pl-6 pr-3 py-2 bg-zinc-900 border border-zinc-700 rounded text-xs text-zinc-100 placeholder:text-zinc-600 focus:outline-none focus:border-emerald-500 focus:ring-1 focus:ring-emerald-500 font-mono disabled:opacity-50"
        />
      </div>
      <button
        type="submit"
        disabled={isLoading || !input.trim()}
        className="w-full px-3 py-1.5 bg-emerald-600 hover:bg-emerald-500 disabled:bg-zinc-700 disabled:text-zinc-500 text-white text-xs font-medium rounded transition-colors"
      >
        {isLoading ? "Running..." : "Run"}
      </button>
    </form>
  );
}
