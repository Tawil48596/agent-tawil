import { create } from "zustand";
import type { Session } from "@/types/chat";
import { api } from "@/lib/api";

interface SessionState {
  sessions: Session[];
  load: () => Promise<void>;
  remove: (id: string) => Promise<void>;
  search: (q: string) => Promise<Session[]>;
}

export const useSessionStore = create<SessionState>((set) => ({
  sessions: [],
  load: async () => { const d = await api.listSessions(); set({ sessions: d.items || [] }); },
  remove: async (id) => { await api.deleteSession(id); set((s) => ({ sessions: s.sessions.filter((x) => x.id !== id) })); },
  search: async (q) => { const d = await api.listSessions(); return (d.items || []).filter((s: Session) => s.title?.includes(q)); },
}));
