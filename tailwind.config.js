module.exports = {
  content: ["./templates/**/*.html", "./static/src/**/*.{js,ts}"] ,
  theme: {
    extend: {
      colors: {
        primary: {
          50: "#e0f2ff",
          100: "#cce0ff",
          200: "#99c2ff",
          300: "#66a3ff",
          400: "#3385ff",
          500: "#0066ff",
          600: "#0052cc",
          700: "#003d99",
          800: "#002966",
          900: "#001433",
          DEFAULT: "#0052cc",
        },
        secondary: { DEFAULT: "#047857" },
      },
      fontFamily: { sans: ["Inter", "ui-sans-serif", "system-ui"] },
    },
  },
  plugins: [require("@tailwindcss/forms"), require("@tailwindcss/typography")],
};
