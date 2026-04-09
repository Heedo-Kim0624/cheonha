/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{vue,js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        primary: {
          DEFAULT: '#C8D530',
          light: '#F4F7D6',
          dark: '#7A8A00',
        },
        text: {
          DEFAULT: '#1A1A1A',
          secondary: '#666',
          tertiary: '#999',
        },
        bg: {
          DEFAULT: '#F5F5F5',
          card: '#FFF',
        },
        border: {
          DEFAULT: '#E5E5E5',
          light: '#F0F0F0',
        },
        danger: '#E74C3C',
        success: '#27AE60',
        warning: '#F39C12',
        info: '#2980B9',
      },
      spacing: {
        sidebar: '220px',
      },
      fontSize: {
        xs: '16px',
        sm: '16px',
        base: '17px',
        lg: '18px',
        xl: '22px',
        '2xl': '26px',
      },
    },
  },
  plugins: [],
}
