import { create } from "zustand";

interface UIState {
  sidebarOpen: boolean;
  contextPanelOpen: boolean;
  toggleSidebar: () => void;
  setSidebarOpen: (open: boolean) => void;
  toggleContextPanel: () => void;
}

export const useUIStore = create<UIState>((set) => ({
  sidebarOpen: typeof window !== "undefined"
    ? window.matchMedia("(min-width: 1024px)").matches
    : true,
  contextPanelOpen: true,
  toggleSidebar: () => set((s) => ({ sidebarOpen: !s.sidebarOpen })),
  setSidebarOpen: (sidebarOpen) => set({ sidebarOpen }),
  toggleContextPanel: () => set((s) => ({ contextPanelOpen: !s.contextPanelOpen })),
}));
