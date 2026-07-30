import { useState, useCallback } from "react";
import type { SSEEvent } from "@/types/chat";
import { api } from "@/lib/api";

export function useSSE() {
  const [streaming, setStreaming] = useState(false);
  const [content, setContent] = useState("");

  const send = useCallback(async (sessionId: string, text: string, model?: string) => {
    setStreaming(true); setContent("");
    try {
      const resp = await api.sendMessage(sessionId, text, model);
      const reader = resp.body?.getReader(); if (!reader) return;
      const decoder = new TextDecoder(); let buf = "", full = "";
      while (true) {
        const { done, value } = await reader.read(); if (done) break;
        buf += decoder.decode(value, { stream: true });
        const lines = buf.split("\n"); buf = lines.pop() || "";
        for (const l of lines) {
          if (!l.startsWith("data: ")) continue;
          try {
            const d: SSEEvent = JSON.parse(l.slice(6));
            if (d.type === "text") { full += d.content || ""; setContent(full); }
            else if (d.type === "done") { setContent(d.content || full); }
          } catch {}
        }
      }
      return full;
    } finally { setStreaming(false); }
  }, []);

  return { streaming, content, send };
}
