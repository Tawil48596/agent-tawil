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
  // Actions
  init: () => Promise<void>;
  createSession: () => Promise<string>;
  selectSession: (id: string) => Promise<void>;
  loadSessions: () => Promise<void>;
  sendMessage: (text: string) => Promise<void>;
  setModel: (m: string) => void;
  setTask: (t: string) => void;
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

  init: async () => {
    try {
      const [modelsData, toolsData, sessions] = await Promise.all([
        api.getModels(), api.listTools(), api.listSessions(),
      ]);
      set({ models: modelsData.available_models?.map((n: string) => ({ name: n, provider: "", available: true, context_length: 0, supports_vision: false, supports_tools: true })) as ModelInfo[] || [],
            tools: toolsData.tools as ToolDef[] || [],
            sessions: sessions.items as Session[] || [] });
    } catch {}
  },

  createSession: async () => {
    const s = await api.createSession("新对话");
    set((st) => ({ sessions: [s, ...st.sessions], activeId: s.id, messages: [] }));
    return s.id;
  },

  selectSession: async (id) => {
    set({ activeId: id });
    try {
      const data = await api.getMessages(id);
      set({ messages: data.items as Message[] || [] });
    } catch { set({ messages: [] }); }
  },

  loadSessions: async () => {
    try {
      const data = await api.listSessions();
      set({ sessions: data.items as Session[] || [] });
    } catch {}
  },

  sendMessage: async (text) => {
    let sid = get().activeId;
    if (!sid) sid = await get().createSession();
    if (!sid) return;

    const userMsg: Message = { id: Date.now(), session_id: sid, role: "user", content: text, created_at: new Date().toISOString() };
    set((st) => ({ messages: [...st.messages, userMsg], streaming: true, streamContent: "" }));

    try {
      const resp = await api.sendMessage(sid, text, get().model || undefined, get().task);
      const reader = resp.body?.getReader();
      if (!reader) return;
      const decoder = new TextDecoder();
      let full = "", buf = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buf += decoder.decode(value, { stream: true });
        const lines = buf.split("\n"); buf = lines.pop() || "";
        for (const l of lines) {
          if (!l.startsWith("data: ")) continue;
          try {
            const d = JSON.parse(l.slice(6));
            if (d.type === "text") { full += d.content || ""; set({ streamContent: full }); }
            else if (d.type === "done") { full = d.content || full; set({ streamContent: "" }); }
          } catch {}
        }
      }
      if (full) {
        const asst: Message = { id: Date.now() + 1, session_id: sid, role: "assistant", content: full, created_at: new Date().toISOString() };
        set((st) => ({ messages: [...st.messages, asst] }));
      }
    } catch (e: any) {
      const err: Message = { id: Date.now() + 2, session_id: sid, role: "system", content: `❌ 请求失败: ${e.message}`, created_at: new Date().toISOString() };
      set((st) => ({ messages: [...st.messages, err] }));
    }
    set({ streaming: false, streamContent: "" });
    get().loadSessions();
  },

  setModel: (m) => set({ model: m }),
  setTask: (t) => set({ task: t }),
}));
