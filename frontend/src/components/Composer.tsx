// 底部输入区：textarea 自适应高度，Enter 发送 / Shift+Enter 换行；发送中变为「停止」按钮
import { useEffect, useRef, useState, type KeyboardEvent } from 'react';
import { Send, Square } from 'lucide-react';

interface ComposerProps {
  sending: boolean;
  onSend: (text: string) => void;
  onStop: () => void;
}

const MAX_HEIGHT = 160; // 输入框最大像素高度，超出后内部滚动

export default function Composer({ sending, onSend, onStop }: ComposerProps) {
  const [text, setText] = useState('');
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // 根据内容自适应高度（先置 auto 再取 scrollHeight）
  const resize = () => {
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = 'auto';
    el.style.height = `${Math.min(el.scrollHeight, MAX_HEIGHT)}px`;
  };

  useEffect(() => {
    resize();
  }, [text]);

  const submit = () => {
    const trimmed = text.trim();
    if (!trimmed || sending) return;
    onSend(trimmed);
    setText('');
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    // 中文输入法组词期间的 Enter 不触发发送
    if (e.key === 'Enter' && !e.shiftKey && !e.nativeEvent.isComposing) {
      e.preventDefault();
      submit();
    }
  };

  return (
    <div className="border-t border-hairline bg-card p-3">
      <div className="flex items-end gap-2 rounded-2xl border border-hairline bg-card p-2 shadow-sm transition-colors focus-within:border-sakura focus-within:ring-2 focus-within:ring-blush">
        <textarea
          ref={textareaRef}
          value={text}
          rows={1}
          maxLength={2000} // 与后端 ChatRequest 约束一致
          placeholder="输入问题，Enter 发送，Shift+Enter 换行"
          className="max-h-40 flex-1 resize-none bg-transparent px-2 py-1.5 text-sm leading-relaxed text-ink outline-none placeholder:text-ink-faint"
          onChange={(e) => setText(e.target.value)}
          onKeyDown={handleKeyDown}
        />
        {sending ? (
          <button
            type="button"
            onClick={onStop}
            className="flex shrink-0 items-center gap-1.5 rounded-xl bg-panel px-3.5 py-2 text-sm font-medium text-ink-soft transition-colors hover:bg-blush"
          >
            <Square className="h-3.5 w-3.5" />
            停止
          </button>
        ) : (
          <button
            type="button"
            onClick={submit}
            disabled={!text.trim()}
            className="flex shrink-0 items-center gap-1.5 rounded-xl bg-sakura px-3.5 py-2 text-sm font-medium text-white transition-colors hover:bg-sakura-deep disabled:cursor-not-allowed disabled:opacity-40"
          >
            <Send className="h-3.5 w-3.5" />
            发送
          </button>
        )}
      </div>
    </div>
  );
}
