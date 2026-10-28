import type { Config } from "tailwindcss";

const config: Config = {
  darkMode: "class",
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        forest: {
          950: '#060f0b',
          900: '#0c1d15',
          850: '#11291e',
          800: '#173628',
          700: '#204a37',
          600: '#2a5f47',
          500: '#387c5e',
          400: '#4da17b',
        },
        bronze: {
          900: '#422e17',
          800: '#5e4120',
          700: '#7d5729',
          600: '#9e6e34',
          500: '#be8743',
          400: '#d9a15b',
          300: '#eac082',
          200: '#f4dcab',
          100: '#faedd4',
        },
      },
    },
  },
  plugins: [],
};
export default config;
