import type { Config } from "tailwindcss";

export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  darkMode: "class",
  theme: {
    extend: {
      colors: {
        bg: "#0f1117",
        surface: "#1a1d27",
        border: "#2a2d3a",
        accent: "#6c8cff",
        dim: "#8b8fa3",
      },
    },
  },
  plugins: [],
} satisfies Config;
