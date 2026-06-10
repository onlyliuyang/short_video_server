/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ["./src/**/*.{js,ts,jsx,tsx,mdx}"],
  theme: {
    extend: {
      colors: {
        background: "var(--background)",
        foreground: "var(--foreground)",
        muted: "var(--muted)",
        border: "var(--border)",
        card: "var(--card)",
        accent: "var(--accent)",
        "accent-soft": "var(--accent-soft)",
      },
      boxShadow: {
        glow: "0 0 40px rgba(102, 126, 234, 0.15)",
      },
    },
  },
  plugins: [],
};
