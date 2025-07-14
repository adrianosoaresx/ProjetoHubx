module.exports = {
  content: ["./templates/**/*.html", "./static/src/**/*.{js,ts}"] ,
  theme: {
    extend: {
      colors: {
        primary: { DEFAULT: "#3B82F6" },
        secondary: { DEFAULT: "#10B981" },
      },
      fontFamily: { sans: ["Inter", "ui-sans-serif", "system-ui"] },
    },
  },
  plugins: [require("@tailwindcss/forms"), require("@tailwindcss/typography")],
};
