// 单条消息气泡：用户消息右侧 indigo 底，助手消息左侧白卡片；助手消息下方渲染参考来源
import { Bot, AlertCircle } from 'lucide-react';
import type { Source } from '../types';
import SourceCard from './SourceCard';

export interface MessageBubbleProps {
  role: 'user' | 'assistant';
  content: string;
  sources?: Source[];
  errorText?: string;
}

export default function MessageBubble({ role, content, sources, errorText }: MessageBubbleProps) {
  if (role === 'user') {
    return (
      <div className="flex justify-end">
        <div className="max-w-[85%] whitespace-pre-wrap break-words rounded-2xl rounded-br-md bg-indigo-600 px-4 py-2.5 text-sm leading-relaxed text-white shadow-sm">
          {content}
        </div>
      </div>
    );
  }

  return (
    <div className="flex items-start gap-2.5">
      <span className="mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-indigo-600 text-white">
        <Bot className="h-4 w-4" />
      </span>
      <div className="min-w-0 max-w-[85%] space-y-2">
        <div className="whitespace-pre-wrap break-words rounded-2xl rounded-tl-md border border-slate-200 bg-white px-4 py-2.5 text-sm leading-relaxed shadow-sm">
          {content || <span className="text-slate-400">思考中…</span>}
        </div>

        {errorText && (
          <div className="flex items-center gap-1.5 rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-xs text-red-600">
            <AlertCircle className="h-3.5 w-3.5 shrink-0" />
            <span>{errorText}</span>
          </div>
        )}

        {sources && sources.length > 0 && (
          <div className="space-y-1.5">
            <p className="text-xs text-slate-400">参考来源</p>
            {sources.map((s, i) => (
              <SourceCard key={s.chunk_id} source={s} index={i} />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
