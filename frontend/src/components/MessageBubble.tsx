// 单条消息气泡：用户消息右侧樱粉底，助手消息左侧近白卡片；助手消息下方渲染参考来源
import { Bot, AlertCircle, Zap } from 'lucide-react';
import type { Source } from '../types';
import SourceCard from './SourceCard';

export interface MessageBubbleProps {
  role: 'user' | 'assistant';
  content: string;
  sources?: Source[];
  errorText?: string;
  cached?: boolean;
}

export default function MessageBubble({
  role,
  content,
  sources,
  errorText,
  cached,
}: MessageBubbleProps) {
  if (role === 'user') {
    return (
      <div className="flex justify-end">
        <div className="max-w-[85%] whitespace-pre-wrap break-words rounded-2xl rounded-br-md bg-sakura px-4 py-2.5 text-sm leading-relaxed text-white shadow-sm">
          {content}
        </div>
      </div>
    );
  }

  return (
    <div className="flex items-start gap-2.5">
      <span className="mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-sakura text-white">
        <Bot className="h-4 w-4" />
      </span>
      <div className="min-w-0 max-w-[85%] space-y-2">
        <div className="whitespace-pre-wrap break-words rounded-2xl rounded-tl-md border border-hairline bg-card px-4 py-2.5 text-sm leading-relaxed text-ink-soft shadow-sm">
          {content || <span className="text-ink-faint">思考中…</span>}
          {cached && content && (
            <span className="ml-2 inline-flex items-center gap-0.5 rounded-full bg-blush px-1.5 py-0.5 align-middle text-[10px] font-medium text-rose-ink">
              <Zap className="h-2.5 w-2.5" />
              来自缓存
            </span>
          )}
        </div>

        {errorText && (
          <div className="flex items-center gap-1.5 rounded-lg border border-bad-bg bg-bad-bg px-3 py-2 text-xs text-bad-fg">
            <AlertCircle className="h-3.5 w-3.5 shrink-0" />
            <span>{errorText}</span>
          </div>
        )}

        {sources && sources.length > 0 && (
          <div className="space-y-1.5">
            <p className="text-xs text-ink-faint">参考来源</p>
            {sources.map((s, i) => (
              <SourceCard key={s.chunk_id} source={s} index={i} />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
