import { create } from "zustand";
import type { ToolDef } from "@/types/chat";
import { api } from "@/lib/api";

interface ToolState {
  tools: ToolDef[];
  load: () => Promise<void>;
}

export const useToolStore = create<ToolState>((set) => ({
  tools: [],
  load: async () => { const d = await api.listTools(); set({ tools: d.tools || [] }); },
}));
