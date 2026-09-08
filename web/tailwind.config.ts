import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: "#111827",
        line: "#d8dee8",
        paper: "#f7f8fb",
        accent: "#0f766e",
        warn: "#b45309"
      }
    }
  },
  plugins: []
};

export default config;
