// 顶部导航 + 路由出口（主题体系与「音阅」同源：樱花/素笺/未来三主题可切换）
import { useEffect } from 'react';
import { Navigate, NavLink, Route, Routes } from 'react-router-dom';
import { Library, MessageSquare, Sparkles } from 'lucide-react';
import ChatPage from './pages/ChatPage';
import DocumentsPage from './pages/DocumentsPage';
import BgArt from './components/BgArt';
import { Charms, Petals } from './components/decor';
import { THEMES, initTheme, setTheme, useTheme } from './theme';

const navLinkCls = ({ isActive }: { isActive: boolean }) =>
  `flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-sm transition-colors ${
    isActive
      ? 'bg-blush font-medium text-rose-ink'
      : 'text-ink-faint hover:bg-panel hover:text-ink-soft'
  }`;

/** 主题切换器：音阅同款分段按钮（风格） */
function ThemeSwitcher() {
  const theme = useTheme();
  return (
    <div
      className="flex overflow-hidden rounded-lg border border-hairline bg-card"
      role="group"
      aria-label="主题风格"
    >
      {THEMES.map(([value, label]) => (
        <button
          key={value}
          onClick={() => setTheme(value)}
          className={`px-2 py-1 text-xs transition-colors ${
            theme === value ? 'bg-blush font-medium text-rose-ink' : 'text-ink-faint hover:text-ink-soft'
          }`}
        >
          {label}
        </button>
      ))}
    </div>
  );
}

export default function App() {
  // 挂载后同步 localStorage 里的主题选择（首帧已由 index.html 内联脚本预设）
  useEffect(() => initTheme(), []);

  return (
    <div className="theme-fade min-h-screen text-ink">
      {/* 全屏装饰层：花瓣（仅樱花）+ 背景美图（樱花/未来） */}
      <Petals />
      <BgArt />

      {/* 顶部导航 */}
      <header className="sticky top-0 z-20 border-b border-hairline glass-card backdrop-blur">
        {/* 挂件挂在导航底边（樱花/未来主题，md 以上才显示） */}
        <Charms />
        <div className="mx-auto flex h-14 max-w-3xl items-center justify-between gap-2 px-4">
          <div className="flex items-center gap-2">
            <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-sakura text-white">
              <Sparkles className="h-5 w-5" />
            </span>
            <span className="text-lg font-semibold tracking-wide">
              EchoMind <span className="text-sakura">回声</span>
            </span>
          </div>
          <nav className="flex items-center gap-2">
            <NavLink to="/" end className={navLinkCls}>
              <MessageSquare className="h-4 w-4" />
              对话
            </NavLink>
            <NavLink to="/documents" className={navLinkCls}>
              <Library className="h-4 w-4" />
              知识库
            </NavLink>
            <ThemeSwitcher />
          </nav>
        </div>
      </header>

      {/* 主区域 */}
      <main className="relative z-10 mx-auto max-w-3xl px-4">
        <Routes>
          <Route path="/" element={<ChatPage />} />
          <Route path="/documents" element={<DocumentsPage />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </main>
    </div>
  );
}
