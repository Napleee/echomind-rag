/** @type {import('tailwindcss').Config} */
// 樱花主题色板移植自「音阅 yinyue-meeting」——同一产品线的姐妹项目，视觉一脉相承
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      fontFamily: {
        // 正文用霞鹜文楷（与音阅一致），回退系统字体
        sans: [
          '"LXGW WenKai"',
          '"LXGW WenKai Lite"',
          '"Songti SC"',
          '"Microsoft YaHei"',
          'system-ui',
          'sans-serif',
        ],
      },
      colors: {
        // 奶油与樱粉（取自音阅 globals.css 语义变量）
        cream: '#fff9f4', // 页面底：奶油白
        panel: '#fdeef3', // 面板：樱花奶油
        card: '#fffdfb', // 卡片：近白
        ink: { DEFAULT: '#4a3f42', soft: '#7a6b70', faint: '#b3a4aa' }, // 暖墨三阶
        hairline: '#f2dfe6', // 细边线
        sakura: { DEFAULT: '#e8608a', deep: '#c94f78' }, // 主粉：强调 / 悬停
        'rose-ink': '#9d3a5c', // 玫瑰墨：强调文字
        blush: '#ffe9f1', // 浅粉底：选中 / 聚焦
        sky: '#a8d8ef', // 天空蓝：第二点缀
        mint: '#5c8a5e', // 就绪状态
        success: { bg: '#e2f1e4', fg: '#5c8a5e' }, // 成功徽标
        bad: { bg: '#f8d7d0', fg: '#c94f78' }, // 失败徽标
      },
    },
  },
  plugins: [],
};
