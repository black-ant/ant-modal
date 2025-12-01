/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        primary: {
          50: '#f0f9f7',
          100: '#d9f2ed',
          200: '#b3e5db',
          300: '#8dd8c9',
          400: '#6fb1a0',
          500: '#5a9d95',
          600: '#4a8d85',
          700: '#3a7d75',
          800: '#2a6d65',
          900: '#1a5d55',
        },
        accent: {
          yellow: '#f5d547',
          orange: '#f5a962',
        },
        background: {
          DEFAULT: '#f5f7fa',
          card: '#ffffff',
        },
      },
      fontFamily: {
        sans: ['-apple-system', 'BlinkMacSystemFont', '"Segoe UI"', 'Roboto', '"Helvetica Neue"', 'Arial', 'sans-serif'],
      },
      borderRadius: {
        'DEFAULT': '0.5rem',
        'lg': '0.75rem',
        'xl': '1rem',
      },
      boxShadow: {
        'card': '0 2px 8px rgba(0, 0, 0, 0.05)',
        'card-hover': '0 4px 12px rgba(0, 0, 0, 0.1)',
      },
    },
  },
  plugins: [],
}
