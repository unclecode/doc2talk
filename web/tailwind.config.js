/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    './src/**/*.{js,jsx,ts,tsx}',
    './public/index.html',
  ],
  theme: {
    extend: {
      colors: {
        gray: {
          900: '#1a1a1a', // Background
          800: '#252526', // Code blocks, inputs
          700: '#333333', // Borders
          600: '#555555', // Disabled buttons
          400: '#888888', // Secondary text
        },
        blue: {
          700: '#2662c7', // Button hover
          600: '#0E639C', // Primary button
          500: '#007ACC', // Focus ring
          400: '#3794FF', // Loading dots
        },
      },
    },
  },
  plugins: [
    require('@tailwindcss/typography'),
  ],
};