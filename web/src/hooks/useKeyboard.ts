import { useEffect } from "react";

export function useKeyboard(handlers: Record<string, () => void>) {
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      const key = (e.ctrlKey || e.metaKey ? "Ctrl+" : "") + e.key;
      if (handlers[key]) { e.preventDefault(); handlers[key](); }
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [handlers]);
}
