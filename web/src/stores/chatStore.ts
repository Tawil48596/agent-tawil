import { create } from "zustand";
import type { Session, Message, ModelInfo, ToolDef } from "@/types/chat";
import { api } from "@/lib/api";

interface ChatState {
  sessions: Session[];
  activeId: string | null;
  messages: Message[];
  model: string;
  task: string;
  models: ModelInfo[];
  tools: ToolDef[];
  streaming: boolean;
  streamContent: string;
  error: string | null;
  // Actions
  init: () => Promise<void>;
  createSession: () => Promise<string>;
  selectSession: (id: string) => Promise<void>;
  loadSessions: () => Promise<void>;
  sendMessage: (text: string) => Promise<void>;
  setModel: (m: string) => void;
  setTask: (t: string) => void;
  clearError: () => void;
}

export const useChatStore = create<ChatState>((set, get) => ({
  sessions: [],
  activeId: null,
  messages: [],
  model: "",
  task: "reasoning",
  models: [],
  tools: [],
  streaming: false,
  streamContent: "",
  error: null,

  init: async () => {
    try {
      const [modelsData, toolsData, sessionsData] = await Promise.all([
        api.getModels().catch(() => ({ available_models: [], models: [] })),
        api.listTools().catch(() => ({ tools: [] })),
        api.listSessions().catch(() => ({ items: [] })),
      ]);
      const ms: ModelInfo[] = (modelsData.available_models || []).map((n: string) => ({
        name: n, provider: "", available: true,
        context_length: 0, supports_vision: false, supports_tools: true,
      }));
      set({ models: ms, tools: toolsData.tools || [], sessions: sessionsData.items || [] });
    } catch (e) {
      console.warn("Failed to initialize:", e);
    }
  },

  createSession: async () => {
    const s = await api.createSession("新对话");
    set((st) => ({ sessions: [s, ...st.sessions], activeId: s.id, messages: [], error: null }));
    return s.id;
  },

  selectSession: async (id) => {
    set({ activeId: id, error: null });
    try {
      const data = await api.getMessages(id);
      set({ messages: data.items || [] });
    } catch { set({ messages: [] }); }
  },

  loadSessions: async () => {
    try {
      const data = await api.listSessions();
      set({ sessions: data.items || [] });
    } catch {}
  },

  sendMessage: async (text) => {
    let sid = get().activeId;
    if (!sid) {
      try {
        sid = await get().createSession();
        // Navigate after creating session
        if (typeof window !== "undefined") {
          window.history.pushState(null, "", `/chat/${sid}`);
        }
      } catch {
        set({ error: "无法创建会话" });
        return;
      }
    }

    set({ error: null, streaming: true, streamContent: "" });

    // Add user message immediately
    const userMsg: Message = {
      id: Date.now(), session_id: sid, role: "user" as const,
      content: text, created_at: new Date().toISOString(),
    };
    set((st) => ({ messages: [...st.messages, userMsg] }));

    let fullText = "";
    try {
      const { model, task } = get();
      const resp = await api.sendMessage(sid, text, model || undefined, task);
      if (!resp.ok) {
        const errText = await resp.text();
        throw new Error(`${resp.status}: ${errText}`);
      }

      const reader = resp.body?.getReader();
      if (!reader) throw new Error("No response body");

      const decoder = new TextDecoder();
      let buf = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buf += decoder.decode(value, { stream: true });
        const lines = buf.split("\n");
        buf = lines.pop() || "";

        for (const l of lines) {
          const trimmed = l.trim();
          if (!trimmed.startsWith("data:")) continue;

          const jsonStr = trimmed.slice(5).trim();
          if (!jsonStr) continue;

          try {
            const d = JSON.parse(jsonStr);
            switch (d.type) {
              case "text":
                fullText += d.content || "";
                set({ streamContent: fullText });
                break;
              case "done":
                if (d.content) fullText = d.content;
                set({ streamContent: "" });
                break;
              case "error":
                set({ error: d.message || "未知错误" });
                break;
              case "thinking":
                set({ streamContent: "💭 " + (d.content || "思考中...") });
                break;
            }
          } catch {
            // skip malformed JSON chunks
          }
        }
      }

      // Save assistant message
      if (fullText) {
        const asstMsg: Message = {
          id: Date.now() + 1, session_id: sid,
          role: "assistant" as const, content: fullText,
          created_at: new Date().toISOString(),
        };
        set((st) => ({ messages: [...st.messages, asstMsg] }));
      }
    } catch (e: any) {
      const msg = e?.message || String(e);
      set({ error: msg.includes("Failed to fetch") ? "无法连接到服务器" : msg });
    } finally {
      set({ streaming: false, streamContent: "" });
      get().loadSessions();
    }
  },

  setModel: (m) => set({ model: m }),
  setTask: (t) => set({ task: t }),
  clearError: () => set({ error: null }),
}));
