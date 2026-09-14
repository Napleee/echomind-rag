// 顶部导航 + 路由出口（樱花主题：奶油纸面 + 樱粉强调，与音阅同源）
import { Navigate, NavLink, Route, Routes } from 'react-router-dom';
import { Library, MessageSquare, Sparkles } from 'lucide-react';
import ChatPage from './pages/ChatPage';
import DocumentsPage from './pages/DocumentsPage';

const navLinkCls = ({ isActive }: { isActive: boolean }) =>
  `flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-sm transition-colors ${
    isActive
      ? 'bg-blush font-medium text-rose-ink'
      : 'text-ink-faint hover:bg-panel hover:text-ink-soft'
  }`;

export default function App() {
  return (
    <div className="min-h-screen text-ink">
      {/* 顶部导航 */}
      <header className="sticky top-0 z-20 border-b border-hairline bg-card/90 backdrop-blur">
        <div className="mx-auto flex h-14 max-w-3xl items-center justify-between px-4">
          <div className="flex items-center gap-2">
            <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-sakura text-white">
              <Sparkles className="h-5 w-5" />
            </span>
            <span className="text-lg font-semibold tracking-wide">
              EchoMind <span className="text-sakura">回声</span>
            </span>
          </div>
          <nav className="flex items-center gap-1">
            <NavLink to="/" end className={navLinkCls}>
              <MessageSquare className="h-4 w-4" />
              对话
            </NavLink>
            <NavLink to="/documents" className={navLinkCls}>
              <Library className="h-4 w-4" />
              知识库
            </NavLink>
          </nav>
        </div>
      </header>

      {/* 主区域 */}
      <main className="mx-auto max-w-3xl px-4">
        <Routes>
          <Route path="/" element={<ChatPage />} />
          <Route path="/documents" element={<DocumentsPage />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </main>
    </div>
  );
}
