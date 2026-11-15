/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      fontFamily: {
        sans: [
          'Inter',
          'Noto Sans Devanagari',
          '-apple-system',
          'BlinkMacSystemFont',
          'Segoe UI',
          'Roboto',
          'sans-serif',
        ],
      },
      colors: {
        paytm: {
          navy: "#002E6E",
          "navy-hover": "#002352",
          cyan: "#00BAF2",
          "cyan-light": "#E5F6FD",
          "cyan-hover": "#00A3D6",
          blue: "#00BAF2",
          dark: "#002E6E",
          accent: "#00B9F5",
        },
        surface: {
          canvas: "#F5F7FA",
          card: "#FFFFFF",
          subtle: "#F0F3F7",
          border: "#E2E8F0",
          divider: "#EDF2F7",
        },
        ink: {
          primary: "#0F1E36",
          secondary: "#4A5568",
          muted: "#718096",
          disabled: "#A0AEC0",
        },
        status: {
          new: {
            bg: "#EFF6FF",
            text: "#1D4ED8",
            border: "#BFDBFE",
          },
          progress: {
            bg: "#F0FDF4",
            text: "#15803D",
            border: "#BBF7D0",
          },
          approval: {
            bg: "#FFF7ED",
            text: "#C2410C",
            border: "#FED7AA",
          },
          verifying: {
            bg: "#F0F9FF",
            text: "#0284C7",
            border: "#BAE6FD",
          },
          resolved: {
            bg: "#ECFDF5",
            text: "#047857",
            border: "#86EFAC",
          },
          rejected: {
            bg: "#FEF2F2",
            text: "#B91C1C",
            border: "#FECACA",
          },
        },
      },
      boxShadow: {
        card: "0 2px 12px 0 rgba(0, 0, 0, 0.04), 0 1px 3px 0 rgba(0, 0, 0, 0.02)",
        paytm: "0 4px 20px -2px rgba(0, 46, 110, 0.08)",
        modal: "0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04)",
      },
      borderRadius: {
        card: "16px",
        chip: "9999px",
        btn: "10px",
        pill: "9999px",
      },
    },
  },
  plugins: [],
}
