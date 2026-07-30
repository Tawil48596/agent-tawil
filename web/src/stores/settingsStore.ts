import { create } from "zustand";

interface SettingsState {
  theme: "dark" | "light";
  language: string;
  setTheme: (t: "dark" | "light") => void;
}

export const useSettingsStore = create<SettingsState>((set) => ({
  theme: "dark", language: "zh",
  setTheme: (t) => set({ theme: t }),
}));
