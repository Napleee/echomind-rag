// 知识库页：文档上传 + 列表管理（重新索引 / 删除），存在处理中文档时每 2 秒轮询刷新
import { useCallback, useEffect, useState } from 'react';
import { AlertCircle, Loader2, RefreshCw, Trash2 } from 'lucide-react';
import { deleteDocument, listDocuments, reindexDocument } from '../api';
import type { Document as DocumentItem } from '../types';
import StatusBadge from '../components/StatusBadge';
import UploadBox from '../components/UploadBox';

const TYPE_LABEL: Record<string, string> = {
  pdf: 'PDF',
  docx: 'Word',
  md: 'MD',
  txt: 'TXT',
  json: 'JSON',
  meeting_json: '会议记录',
};

function typeLabel(t: string): string {
  return TYPE_LABEL[t] ?? t.toUpperCase();
}

function fmtTime(iso: string): string {
  const d = new Date(iso);
  return Number.isNaN(d.getTime()) ? iso : d.toLocaleString('zh-CN', { hour12: false });
}

export default function DocumentsPage() {
  const [docs, setDocs] = useState<DocumentItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [busyId, setBusyId] = useState<number | null>(null); // 正在执行操作（重索引/删除）的文档

  const refresh = useCallback(async () => {
    try {
      const list = await listDocuments();
      setDocs(list);
      setError(null);
    } catch (err) {
      setError(`加载文档列表失败：${(err as Error).message}`);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  // 存在处理中文档时每 2 秒轮询刷新
  const hasProcessing = docs.some((d) => d.status === 'processing');
  useEffect(() => {
    if (!hasProcessing) return;
    const timer = window.setInterval(() => {
      void refresh();
    }, 2000);
    return () => window.clearInterval(timer);
  }, [hasProcessing, refresh]);

  const handleReindex = async (doc: DocumentItem) => {
    setBusyId(doc.id);
    setError(null);
    try {
      await reindexDocument(doc.id);
      await refresh();
    } catch (err) {
      setError(`重新索引失败：${(err as Error).message}`);
    } finally {
      setBusyId(null);
    }
  };

  const handleDelete = async (doc: DocumentItem) => {
    if (!window.confirm(`确定删除「${doc.title}」吗？其全部分段将一并删除，操作不可恢复。`)) {
      return;
    }
    setBusyId(doc.id);
    setError(null);
    try {
      await deleteDocument(doc.id);
      await refresh();
    } catch (err) {
      setError(`删除失败：${(err as Error).message}`);
    } finally {
      setBusyId(null);
    }
  };

  return (
    <div className="space-y-5 py-6">
      <div>
        <h1 className="text-lg font-semibold text-slate-800">知识库</h1>
        <p className="mt-1 text-sm text-slate-400">
          上传文档，自动切块并向量化入库，随后即可在对话中检索。
        </p>
      </div>

      <UploadBox onUploaded={() => void refresh()} />

      {error && (
        <div className="flex items-center gap-2 rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-600">
          <AlertCircle className="h-4 w-4 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      <div className="overflow-hidden rounded-xl border border-slate-200 bg-white">
        {loading ? (
          <div className="flex items-center justify-center gap-2 py-16 text-sm text-slate-400">
            <Loader2 className="h-4 w-4 animate-spin" />
            加载中…
          </div>
        ) : docs.length === 0 ? (
          <div className="py-16 text-center text-sm text-slate-400">
            还没有文档，先上传一份试试吧
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-slate-200 bg-slate-50 text-left text-xs text-slate-500">
                  <th className="px-4 py-2.5 font-medium">标题</th>
                  <th className="px-3 py-2.5 font-medium">类型</th>
                  <th className="px-3 py-2.5 font-medium">状态</th>
                  <th className="px-3 py-2.5 text-right font-medium">分段</th>
                  <th className="px-3 py-2.5 font-medium">上传时间</th>
                  <th className="px-3 py-2.5 text-right font-medium">操作</th>
                </tr>
              </thead>
              <tbody>
                {docs.map((doc) => (
                  <tr
                    key={doc.id}
                    className="border-b border-slate-100 transition-colors last:border-0 hover:bg-slate-50/60"
                  >
                    <td
                      className="max-w-[220px] truncate px-4 py-2.5 font-medium text-slate-700"
                      title={doc.title}
                    >
                      {doc.title}
                    </td>
                    <td className="px-3 py-2.5">
                      <span className="rounded bg-slate-100 px-1.5 py-0.5 text-xs text-slate-500">
                        {typeLabel(doc.source_type)}
                      </span>
                    </td>
                    <td className="px-3 py-2.5">
                      <StatusBadge status={doc.status} error={doc.error} />
                    </td>
                    <td className="px-3 py-2.5 text-right tabular-nums text-slate-600">
                      {doc.chunk_count}
                    </td>
                    <td className="whitespace-nowrap px-3 py-2.5 text-xs text-slate-500">
                      {fmtTime(doc.created_at)}
                    </td>
                    <td className="px-3 py-2.5">
                      <div className="flex justify-end gap-1">
                        <button
                          type="button"
                          onClick={() => void handleReindex(doc)}
                          disabled={busyId !== null}
                          title="删除旧分段并重新解析入库"
                          className="inline-flex items-center gap-1 rounded-md px-2 py-1 text-xs text-slate-500 transition-colors hover:bg-indigo-50 hover:text-indigo-600 disabled:cursor-not-allowed disabled:opacity-40"
                        >
                          <RefreshCw
                            className={`h-3.5 w-3.5${busyId === doc.id ? ' animate-spin' : ''}`}
                          />
                          重新索引
                        </button>
                        <button
                          type="button"
                          onClick={() => void handleDelete(doc)}
                          disabled={busyId !== null}
                          className="inline-flex items-center gap-1 rounded-md px-2 py-1 text-xs text-slate-500 transition-colors hover:bg-red-50 hover:text-red-600 disabled:cursor-not-allowed disabled:opacity-40"
                        >
                          <Trash2 className="h-3.5 w-3.5" />
                          删除
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
