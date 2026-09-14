/**
 * 前端类型定义：与后端 app/schemas/__init__.py 一一对应，
 * 另附 SSE 事件载荷类型（与 API 契约中的 SSE 事件格式对齐）。
 */

/** 文档状态机：processing → ready / error（保留 string 以兼容未知值） */
export type DocStatus = 'processing' | 'ready' | 'error' | (string & {});

/** 对应 DocumentOut */
export interface Document {
  id: number;
  title: string;
  source_type: string;
  status: DocStatus;
  chunk_count: number;
  error: string | null;
  created_at: string;
}

/** 对应 DocumentStatusOut */
export interface DocumentStatus {
  id: number;
  status: DocStatus;
  chunk_count: number;
  error: string | null;
}

/** 对应 ChatRequest */
export interface ChatRequest {
  question: string;
  conversation_id?: number | null;
  top_k?: number | null;
}

/** 对应 SourceOut */
export interface Source {
  chunk_id: number;
  document_id: number;
  document_title: string;
  seq: number;
  score: number;
  snippet: string;
}

/** 对应 ConversationOut */
export interface Conversation {
  id: number;
  title: string | null;
  created_at: string;
}

/** 对应 MessageOut */
export interface Message {
  id: number;
  role: string;
  content: string;
  sources: Source[] | null;
  created_at: string;
}

// ---------- SSE 事件载荷 ----------

/** event: sources */
export interface SourcesEvent {
  sources: Source[];
}

/** event: token */
export interface TokenEvent {
  delta: string;
}

/** event: done */
export interface DoneEvent {
  conversation_id: number;
  latency_ms: number;
}

/** event: error */
export interface ErrorEvent {
  message: string;
}
