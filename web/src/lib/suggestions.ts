import type { Transaction } from "./types";

interface Suggestion {
  label: string;
  prompt: string;
}

export function getSuggestions(transactions: Transaction[]): Suggestion[] {
  if (transactions.length === 0) return [];

  const suggestions: Suggestion[] = [];

  const emptyCategories = transactions.filter((t) => !t.category).length;
  const categorizedCount = transactions.length - emptyCategories;
  const maxAmount = Math.max(...transactions.map((t) => Math.abs(t.amount)));
  const totalAmount = transactions.reduce((sum, t) => sum + Math.abs(t.amount), 0);
  const avgAmount = totalAmount / transactions.length;

  // If most transactions are uncategorized → suggest categorize
  if (emptyCategories > transactions.length * 0.5) {
    suggestions.push({
      label: `Categorize ${emptyCategories} uncategorized transaction${emptyCategories !== 1 ? "s" : ""}`,
      prompt: "Categorize all transactions",
    });
  }

  // If transactions are categorized → suggest summary
  if (categorizedCount > transactions.length * 0.5) {
    const categories = new Set(transactions.map((t) => t.category).filter(Boolean));
    suggestions.push({
      label: `Summarize ${categories.size} categor${categories.size !== 1 ? "ies" : "y"}`,
      prompt: "Summarize by category",
    });
  }

  // If there are outlier transactions (> 3x average) → suggest highlight
  if (maxAmount > avgAmount * 3 && maxAmount > 500) {
    const threshold = Math.round(avgAmount * 2 / 100) * 100; // round to nearest 100
    const flagCount = transactions.filter((t) => Math.abs(t.amount) > threshold).length;
    suggestions.push({
      label: `Flag ${flagCount} transaction${flagCount !== 1 ? "s" : ""} over $${threshold.toLocaleString()}`,
      prompt: `Highlight transactions over $${threshold}`,
    });
  }

  return suggestions;
}
