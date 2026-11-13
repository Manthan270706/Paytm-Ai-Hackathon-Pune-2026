/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        paytm: {
          blue: "#00BAF2",
          dark: "#002970",
          navy: "#0F1E36",
          accent: "#00B9F5"
        }
      }
    },
  },
  plugins: [],
}
