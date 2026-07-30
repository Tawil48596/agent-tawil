import { create } from "zustand";

interface UIState {
  sidebarOpen: boolean;
  contextPanelOpen: boolean;
  toggleSidebar: () => void;
  toggleContextPanel: () => void;
}

export const useUIStore = create<UIState>((set) => ({
  sidebarOpen: true,
  contextPanelOpen: true,
  toggleSidebar: () => set((s) => ({ sidebarOpen: !s.sidebarOpen })),
  toggleContextPanel: () => set((s) => ({ contextPanelOpen: !s.contextPanelOpen })),
}));
