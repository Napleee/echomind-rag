// 顶部导航 + 路由出口
import { Navigate, NavLink, Route, Routes } from 'react-router-dom';
import { Library, MessageSquare, Sparkles } from 'lucide-react';
import ChatPage from './pages/ChatPage';
import DocumentsPage from './pages/DocumentsPage';

const navLinkCls = ({ isActive }: { isActive: boolean }) =>
  `flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-sm transition-colors ${
    isActive
      ? 'bg-indigo-50 font-medium text-indigo-600'
      : 'text-slate-500 hover:bg-slate-100 hover:text-slate-700'
  }`;

export default function App() {
  return (
    <div className="min-h-screen bg-slate-50 text-slate-800">
      {/* 顶部导航 */}
      <header className="sticky top-0 z-20 border-b border-slate-200 bg-white/90 backdrop-blur">
        <div className="mx-auto flex h-14 max-w-3xl items-center justify-between px-4">
          <div className="flex items-center gap-2">
            <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-indigo-600 text-white">
              <Sparkles className="h-5 w-5" />
            </span>
            <span className="text-lg font-semibold tracking-wide">
              EchoMind <span className="text-indigo-600">回声</span>
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
