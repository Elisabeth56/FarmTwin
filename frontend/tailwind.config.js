/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        bg: "#F5F7F3",
        card: "#FFFFFF",
        primary: {
          DEFAULT: "#2D7A3E",
          hover: "#245F31",
          tint: "#E8F1EA",
        },
        ink: {
          DEFAULT: "#1A1F1B",
          muted: "#5A625C",
          faint: "#8B948E",
        },
        border: "#E5E9E6",
        risk: {
          high: "#B94A3F",
          medium: "#C89A3F",
          low: "#5A9A8B",
        },
      },
      fontFamily: {
        sans: [
          "-apple-system",
          "BlinkMacSystemFont",
          "Inter",
          "system-ui",
          "sans-serif",
        ],
      },
    },
  },
  plugins: [
    function ({ addUtilities }) {
      addUtilities({
        ".tabular": {
          "font-feature-settings": '"tnum"',
          "font-variant-numeric": "tabular-nums",
        },
      });
    },
  ],
};
