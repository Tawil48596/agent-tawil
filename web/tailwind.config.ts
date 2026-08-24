import type { Config } from "tailwindcss";

export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  darkMode: "class",
  theme: {
    extend: {
      colors: {
        bg: "#0d0d0d",
        surface: "#171717",
        border: "#303030",
        accent: "#e4e4e7",
        dim: "#a1a1aa",
      },
    },
  },
  plugins: [],
} satisfies Config;
