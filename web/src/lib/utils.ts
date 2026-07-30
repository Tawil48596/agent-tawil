import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatTime(iso: string) {
  try { return new Date(iso).toLocaleTimeString(); } catch { return iso; }
}

export function truncate(s: string, len: number) {
  return s.length > len ? s.slice(0, len) + "…" : s;
}
