/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      fontFamily: {
        // 中文环境优先微软雅黑
        sans: ['system-ui', '"Microsoft YaHei"', 'sans-serif'],
      },
    },
  },
  plugins: [],
};
