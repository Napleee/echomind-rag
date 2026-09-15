/** @type {import('tailwindcss').Config} */
// 主题体系移植自「音阅 yinyue-meeting」——姐妹项目共享同一套视觉语言。
// 色板不在配置里写死，而是引用 CSS 变量（index.css 中按 data-theme 切换），
// 这样樱花/素笺/未来三套主题只换变量值，所有语义类名不动。
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
        // 语义色 → 变量（:root 为樱花默认，[data-theme] 覆盖出素笺/未来）
        cream: 'var(--c-cream)',
        panel: 'var(--c-panel)',
        card: 'var(--c-card)',
        ink: { DEFAULT: 'var(--c-ink)', soft: 'var(--c-ink-soft)', faint: 'var(--c-ink-faint)' },
        hairline: 'var(--c-hairline)',
        sakura: { DEFAULT: 'var(--c-sakura)', deep: 'var(--c-sakura-deep)' },
        'rose-ink': 'var(--c-rose-ink)',
        blush: 'var(--c-blush)',
        sky: 'var(--c-sky)',
        mint: 'var(--c-mint)',
        success: { bg: 'var(--c-chip-ok-bg)', fg: 'var(--c-chip-ok-fg)' },
        bad: { bg: 'var(--c-chip-bad-bg)', fg: 'var(--c-chip-bad-fg)' },
      },
    },
  },
  plugins: [],
};
