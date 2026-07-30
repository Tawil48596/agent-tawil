import { useState, useCallback } from "react";

interface MemoryEntry { id: string; content: string; type: string; importance: number; }

export function useMemory() {
  const [memories, setMemories] = useState<MemoryEntry[]>([]);

  const search = useCallback(async (query: string) => {
    try {
      const r = await fetch("/api/v1/memory/search", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ query, limit: 5 }) });
      const d = await r.json(); setMemories(d.results || []);
    } catch { setMemories([]); }
  }, []);

  return { memories, search };
}
