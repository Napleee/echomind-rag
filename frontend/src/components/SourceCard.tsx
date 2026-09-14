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
    <div className="overflow-hidden rounded-lg border border-hairline bg-panel text-xs">
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        className="flex w-full items-center gap-2 px-3 py-2 text-left transition-colors hover:bg-blush/60"
      >
        {open ? (
          <ChevronDown className="h-3.5 w-3.5 shrink-0 text-ink-faint" />
        ) : (
          <ChevronRight className="h-3.5 w-3.5 shrink-0 text-ink-faint" />
        )}
        <FileText className="h-3.5 w-3.5 shrink-0 text-sakura" />
        <span className="truncate font-medium text-ink">{source.document_title}</span>
        <span className="shrink-0 text-ink-faint">
          资料 {index + 1} · 第 {source.seq + 1} 段
        </span>
        <span className="ml-auto shrink-0 rounded-full bg-blush px-2 py-0.5 font-medium tabular-nums text-rose-ink">
          {scorePct}
        </span>
      </button>
      {open && (
        <p className="whitespace-pre-wrap break-words border-t border-hairline bg-card px-3 py-2 leading-relaxed text-ink-soft">
          {source.snippet}
        </p>
      )}
    </div>
  );
}
