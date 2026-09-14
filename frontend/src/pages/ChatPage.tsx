// 对话页：流式问答 + 参考来源溯源 + 多轮会话（done 事件回填 conversation_id）
import { useEffect, useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import { Sparkles } from 'lucide-react';
import { streamChat } from '../api';
import type { Source } from '../types';
import Composer from '../components/Composer';
import MessageBubble from '../components/MessageBubble';

/** 页面内的消息模型（服务端持久化的见 types.ts 的 Message） */
interface ChatMessage {
  id: number;
  role: 'user' | 'assistant';
  content: string;
  sources?: Source[];
  errorText?: string;
}

export default function ChatPage() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [sending, setSending] = useState(false);
  const [conversationId, setConversationId] = useState<number | null>(null);

  const idCounter = useRef(0);
  const abortRef = useRef<AbortController | null>(null);
  const bottomRef = useRef<HTMLDivElement | null>(null);

  // 消息变化（含流式追加）时滚动到底部
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ block: 'end' });
  }, [messages]);

  // 离开页面时中断进行中的请求
  useEffect(() => () => abortRef.current?.abort(), []);

  const patchAssistant = (id: number, patch: Partial<ChatMessage>) => {
    setMessages((prev) => prev.map((m) => (m.id === id ? { ...m, ...patch } : m)));
  };

  const send = async (question: string) => {
    if (sending) return;

    const userId = ++idCounter.current;
    const assistantId = ++idCounter.current;
    setMessages((prev) => [
      ...prev,
      { id: userId, role: 'user', content: question },
      { id: assistantId, role: 'assistant', content: '' },
    ]);
    setSending(true);
    const controller = new AbortController();
    abortRef.current = controller;

    try {
      await streamChat(
        { question, conversation_id: conversationId },
        {
          onSources: (p) => patchAssistant(assistantId, { sources: p.sources }),
          onToken: (p) =>
            setMessages((prev) =>
              prev.map((m) => (m.id === assistantId ? { ...m, content: m.content + p.delta } : m)),
            ),
          onDone: (p) => setConversationId(p.conversation_id),
          onError: (p) => patchAssistant(assistantId, { errorText: p.message }),
        },
        controller.signal,
      );
    } catch (err) {
      const e = err as Error;
      if (e.name === 'AbortError') {
        // 用户主动停止：已有内容则保留，内容为空才提示
        setMessages((prev) =>
          prev.map((m) =>
            m.id === assistantId && !m.content && !m.errorText
              ? { ...m, errorText: '已停止生成。' }
              : m,
          ),
        );
      } else {
        patchAssistant(assistantId, { errorText: e.message });
      }
    } finally {
      setSending(false);
      abortRef.current = null;
    }
  };

  return (
    <div className="flex h-[calc(100vh-3.5rem)] flex-col">
      {/* 消息列表 */}
      <div className="flex-1 space-y-6 overflow-y-auto py-6">
        {messages.length === 0 ? (
          <div className="flex h-full flex-col items-center justify-center px-4 text-center">
            <span className="mb-4 flex h-14 w-14 items-center justify-center rounded-2xl bg-indigo-600 text-white shadow-sm">
              <Sparkles className="h-7 w-7" />
            </span>
            <h2 className="text-lg font-semibold text-slate-700">向你的知识库提问</h2>
            <p className="mt-2 max-w-sm text-sm leading-relaxed text-slate-400">
              EchoMind 回声会先检索你上传的文档，再生成附带来源的回答。
              还没有资料？先到{' '}
              <Link to="/documents" className="font-medium text-indigo-600 hover:underline">
                知识库
              </Link>{' '}
              上传文档吧。
            </p>
          </div>
        ) : (
          messages.map((m) => (
            <MessageBubble
              key={m.id}
              role={m.role}
              content={m.content}
              sources={m.sources}
              errorText={m.errorText}
            />
          ))
        )}
        <div ref={bottomRef} />
      </div>

      {/* 输入区 */}
      <Composer
        sending={sending}
        onSend={(t) => void send(t)}
        onStop={() => abortRef.current?.abort()}
      />
    </div>
  );
}
