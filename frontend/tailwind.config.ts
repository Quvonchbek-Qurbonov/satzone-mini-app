import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        // Telegram theme colors are injected as CSS vars in main.tsx.
        bg: "var(--tg-bg)",
        text: "var(--tg-text)",
        hint: "var(--tg-hint)",
        link: "var(--tg-link)",
        button: "var(--tg-button)",
        buttonText: "var(--tg-button-text)",
        secondaryBg: "var(--tg-secondary-bg)",
        accent: "var(--tg-accent, #2481cc)",
        danger: "#dc3545",
        warning: "#f9a825",
        success: "#28a745",
      },
      fontFamily: {
        sans: [
          "-apple-system",
          "BlinkMacSystemFont",
          "Segoe UI",
          "Roboto",
          "Helvetica",
          "Arial",
          "sans-serif",
        ],
      },
    },
  },
  plugins: [],
};

export default config;
