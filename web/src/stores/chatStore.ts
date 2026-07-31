import { create } from "zustand";
import type { Session, Message, ModelInfo, ToolDef } from "@/types/chat";
import { api } from "@/lib/api";

let activeRequest: AbortController | null = null;

interface ChatState {
  sessions: Session[];
  activeId: string | null;
  messages: Message[];
  model: string;
  task: string;
  reasoningEffort: string;
  toolsEnabled: boolean;
  models: ModelInfo[];
  tools: ToolDef[];
  streaming: boolean;
  streamContent: string;
  interrupted: boolean;
  lastSentText: string;
  error: string | null;
  // Actions
  init: () => Promise<void>;
  createSession: () => Promise<string>;
  selectSession: (id: string) => Promise<void>;
  loadSessions: () => Promise<void>;
  sendMessage: (text: string, retry?: boolean) => Promise<void>;
  stopStreaming: () => void;
  retryLastMessage: () => Promise<void>;
  setModel: (m: string) => void;
  setTask: (t: string) => void;
  setReasoningEffort: (effort: string) => void;
  setToolsEnabled: (enabled: boolean) => void;
  clearError: () => void;
}

export const useChatStore = create<ChatState>((set, get) => ({
  sessions: [],
  activeId: null,
  messages: [],
  model: typeof window !== "undefined" ? localStorage.getItem("ai-agent-default-model") || "" : "",
  task: "reasoning",
  reasoningEffort: typeof window !== "undefined" ? localStorage.getItem("ai-agent-reasoning-effort") || "auto" : "auto",
  toolsEnabled: typeof window !== "undefined" ? localStorage.getItem("ai-agent-tools-enabled") !== "false" : true,
  models: [],
  tools: [],
  streaming: false,
  streamContent: "",
  interrupted: false,
  lastSentText: "",
  error: null,

  init: async () => {
    try {
      const [modelsData, toolsData, sessionsData] = await Promise.all([
        api.getModels().catch(() => ({ available_models: [], models: [] })),
        api.listTools().catch(() => ({ tools: [] })),
        api.listSessions().catch(() => ({ items: [] })),
      ]);
      const ms: ModelInfo[] = (modelsData.models || []).filter((m: ModelInfo) => m.available);
      const savedModel = localStorage.getItem("ai-agent-default-model") || "";
      const model = savedModel && ms.some((m) => m.name === savedModel) ? savedModel : "";
      set({ models: ms, tools: toolsData.tools || [], sessions: sessionsData.items || [], model });
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

  sendMessage: async (text, retry = false) => {
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

    activeRequest?.abort();
    const requestController = new AbortController();
    activeRequest = requestController;
    set({
      error: null,
      streaming: true,
      streamContent: "",
      interrupted: false,
      lastSentText: text,
    });

    // Add user message immediately
    if (!retry) {
      const userMsg: Message = {
        id: Date.now(), session_id: sid, role: "user" as const,
        content: text, created_at: new Date().toISOString(),
      };
      set((st) => ({ messages: [...st.messages, userMsg] }));
    }

    let fullText = "";
    try {
      const { model, task, reasoningEffort, toolsEnabled, tools } = get();
      const enabledToolNames = toolsEnabled
        ? tools.filter((tool) => !tool.is_dangerous).map((tool) => tool.name)
        : [];
      const resp = await api.sendMessage(
        sid, text, model || undefined, task, reasoningEffort, enabledToolNames,
        retry, requestController.signal,
      );
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
              case "tool_calls":
                set({ streamContent: `正在调用 ${d.calls?.length || 0} 个工具…` });
                break;
              case "tool_results":
                set({ streamContent: "工具执行完成，正在整理结果…" });
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
      set({ interrupted: false });
    } catch (e: any) {
      if (e?.name === "AbortError") {
        set({ interrupted: true, error: null });
        return;
      }
      const msg = e?.message || String(e);
      set({ error: msg.includes("Failed to fetch") ? "无法连接到服务器" : msg });
    } finally {
      if (activeRequest === requestController) activeRequest = null;
      set({ streaming: false, streamContent: "" });
      get().loadSessions();
    }
  },

  stopStreaming: () => {
    activeRequest?.abort();
  },

  retryLastMessage: async () => {
    const text = get().lastSentText;
    if (!text || get().streaming) return;
    await get().sendMessage(text, true);
  },

  setModel: (m) => {
    localStorage.setItem("ai-agent-default-model", m);
    set({ model: m });
  },
  setTask: (t) => set({ task: t }),
  setReasoningEffort: (effort) => {
    localStorage.setItem("ai-agent-reasoning-effort", effort);
    set({ reasoningEffort: effort });
  },
  setToolsEnabled: (enabled) => {
    localStorage.setItem("ai-agent-tools-enabled", String(enabled));
    set({ toolsEnabled: enabled });
  },
  clearError: () => set({ error: null }),
}));
