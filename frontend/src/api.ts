/**
 * 后端 API 封装：REST 请求 + 手写 SSE 流式解析。
 * 统一走 /api 前缀（开发期由 Vite 代理到 http://localhost:8000）。
 */
import type {
  ChatRequest,
  Conversation,
  Document,
  DocumentStatus,
  DoneEvent,
  ErrorEvent,
  Message,
  SourcesEvent,
  TokenEvent,
} from './types';

const BASE = '/api';

/** 统一处理非 2xx 响应：尽量解析 FastAPI 的 detail 字段 */
async function ensureOk(resp: Response): Promise<void> {
  if (resp.ok) return;
  let detail = resp.statusText || '未知错误';
  try {
    const body: unknown = await resp.json();
    const d = (body as { detail?: unknown }).detail;
    if (typeof d === 'string') detail = d;
    else if (d !== undefined && d !== null) detail = JSON.stringify(d);
  } catch {
    /* 响应体不是 JSON，忽略 */
  }
  throw new Error(`${resp.status} ${detail}`);
}

async function getJson<T>(path: string): Promise<T> {
  const resp = await fetch(`${BASE}${path}`);
  await ensureOk(resp);
  return (await resp.json()) as T;
}

// ---------- 文档 ----------

/** 上传文档（multipart 字段 file），返回 202 的 DocumentOut */
export async function uploadDocument(file: File): Promise<Document> {
  const form = new FormData();
  form.append('file', file);
  const resp = await fetch(`${BASE}/documents`, { method: 'POST', body: form });
  await ensureOk(resp);
  return (await resp.json()) as Document;
}

/** 文档列表，created_at 倒序 */
export function listDocuments(): Promise<Document[]> {
  return getJson<Document[]>('/documents');
}

/** 删除文档（204 无返回体） */
export async function deleteDocument(id: number): Promise<void> {
  const resp = await fetch(`${BASE}/documents/${id}`, { method: 'DELETE' });
  await ensureOk(resp);
}

/** 重新索引：删除旧 chunks 并重走进库管线（202） */
export async function reindexDocument(id: number): Promise<Document> {
  const resp = await fetch(`${BASE}/documents/${id}/reindex`, { method: 'POST' });
  await ensureOk(resp);
  return (await resp.json()) as Document;
}

/** 单个文档的处理状态 */
export function getStatus(id: number): Promise<DocumentStatus> {
  return getJson<DocumentStatus>(`/documents/${id}/status`);
}

// ---------- 会话 ----------

/** 最新 50 条会话 */
export function getConversations(): Promise<Conversation[]> {
  return getJson<Conversation[]>('/conversations');
}

/** 某会话的全部消息，按 id 升序 */
export function getMessages(id: number): Promise<Message[]> {
  return getJson<Message[]>(`/conversations/${id}/messages`);
}

// ---------- SSE 流式问答 ----------

export interface StreamHandlers {
  onSources?: (payload: SourcesEvent) => void;
  onToken?: (payload: TokenEvent) => void;
  onDone?: (payload: DoneEvent) => void;
  onError?: (payload: ErrorEvent) => void;
}

/** 解析一帧 SSE（event 行 + data 行），分发到对应回调 */
function dispatchFrame(frame: string, handlers: StreamHandlers): void {
  let event = '';
  const dataLines: string[] = [];
  for (const raw of frame.split('\n')) {
    const line = raw.endsWith('\r') ? raw.slice(0, -1) : raw;
    if (line.startsWith('event:')) {
      event = line.slice(6).trim();
    } else if (line.startsWith('data:')) {
      dataLines.push(line.slice(5).trimStart());
    }
  }
  if (!event || dataLines.length === 0) return;

  let payload: unknown;
  try {
    payload = JSON.parse(dataLines.join('\n'));
  } catch {
    return; // data 不是合法 JSON，忽略该帧
  }

  switch (event) {
    case 'sources':
      handlers.onSources?.(payload as SourcesEvent);
      break;
    case 'token':
      handlers.onToken?.(payload as TokenEvent);
      break;
    case 'done':
      handlers.onDone?.(payload as DoneEvent);
      break;
    case 'error':
      handlers.onError?.(payload as ErrorEvent);
      break;
    default:
      break; // 未知事件类型，忽略
  }
}

/**
 * 发起问答请求并解析 SSE 流。
 * 按「空行」分帧，每帧含一行 event 与一行 data（单行 JSON）。
 * 可通过 AbortController 中断（浏览器会以 AbortError reject）。
 */
export async function streamChat(
  req: ChatRequest,
  handlers: StreamHandlers,
  signal?: AbortSignal,
): Promise<void> {
  const resp = await fetch(`${BASE}/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', Accept: 'text/event-stream' },
    body: JSON.stringify(req),
    signal,
  });
  await ensureOk(resp);
  if (!resp.body) throw new Error('响应不包含数据流');

  const reader = resp.body.getReader();
  const decoder = new TextDecoder('utf-8');
  let buffer = '';
  try {
    for (;;) {
      const { done, value } = await reader.read();
      if (done) break;
      // 统一换行符为 \n（跨 chunk 边界的 \r\n 也能正确归一化）
      buffer = (buffer + decoder.decode(value, { stream: true })).replace(/\r\n/g, '\n');
      let sep = buffer.indexOf('\n\n');
      while (sep !== -1) {
        dispatchFrame(buffer.slice(0, sep), handlers);
        buffer = buffer.slice(sep + 2);
        sep = buffer.indexOf('\n\n');
      }
    }
    buffer += decoder.decode(); // 冲刷解码器残余字节
    if (buffer.trim().length > 0) dispatchFrame(buffer, handlers); // 流末尾可能没有空行
  } finally {
    reader.releaseLock();
  }
}
