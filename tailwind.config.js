module.exports = {
  content: ["./templates/**/*.html", "./static/src/**/*.{js,ts}"] ,
  theme: {
    extend: {
      colors: {
        primary: { DEFAULT: "#1D4ED8" },
        secondary: { DEFAULT: "#047857" },
      },
      fontFamily: { sans: ["Inter", "ui-sans-serif", "system-ui"] },
    },
  },
  plugins: [require("@tailwindcss/forms"), require("@tailwindcss/typography")],
};
