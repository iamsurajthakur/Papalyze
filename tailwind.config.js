/** @type {import('tailwindcss').Config} */
module.exports = {
  darkMode: 'class',
  content: [
    "./app/templates/**/*.html",
    "./node_modules/flowbite/**/*.js",
    "./node_modules/preline/**/*.js"
  ],
  safelist: ['text-customBlue', 'hover:text-customBlue'],

  theme: {
    extend: {}
  },
  plugins: [
    require('flowbite/plugin')
  ]
};
