// 参考来源卡片：可折叠，展示文档标题、段落序号、相关度百分比与片段预览
import { useState } from 'react';
import { ChevronDown, ChevronRight, FileText } from 'lucide-react';
import type { Source } from '../types';

interface SourceCardProps {
  source: Source;
  index: number;
}

export default function SourceCard({ source, index }: SourceCardProps) {
  const [open, setOpen] = useState(false);
  // 契约要求 score 以百分比展示
  const scorePct = `${(source.score * 100).toFixed(1)}%`;

  return (
    <div className="overflow-hidden rounded-lg border border-slate-200 bg-slate-50 text-xs">
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        className="flex w-full items-center gap-2 px-3 py-2 text-left transition-colors hover:bg-slate-100"
      >
        {open ? (
          <ChevronDown className="h-3.5 w-3.5 shrink-0 text-slate-400" />
        ) : (
          <ChevronRight className="h-3.5 w-3.5 shrink-0 text-slate-400" />
        )}
        <FileText className="h-3.5 w-3.5 shrink-0 text-indigo-500" />
        <span className="truncate font-medium text-slate-700">{source.document_title}</span>
        <span className="shrink-0 text-slate-400">
          资料 {index + 1} · 第 {source.seq + 1} 段
        </span>
        <span className="ml-auto shrink-0 rounded-full bg-indigo-50 px-2 py-0.5 font-medium tabular-nums text-indigo-600">
          {scorePct}
        </span>
      </button>
      {open && (
        <p className="whitespace-pre-wrap break-words border-t border-slate-200 px-3 py-2 leading-relaxed text-slate-600">
          {source.snippet}
        </p>
      )}
    </div>
  );
}
