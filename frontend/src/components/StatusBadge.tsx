// 文档状态徽标：processing 转圈 / ready 绿色 / error 红色（悬停 title 提示错误信息）
import { Loader2 } from 'lucide-react';

interface StatusBadgeProps {
  status: string;
  error?: string | null;
}

const STYLE: Record<string, { label: string; cls: string }> = {
  processing: { label: '处理中', cls: 'border-amber-200 bg-amber-50 text-amber-600' },
  ready: { label: '就绪', cls: 'border-green-200 bg-green-50 text-green-600' },
  error: { label: '失败', cls: 'border-red-200 bg-red-50 text-red-600' },
};

export default function StatusBadge({ status, error }: StatusBadgeProps) {
  const conf = STYLE[status] ?? { label: status, cls: 'border-slate-200 bg-slate-50 text-slate-500' };
  return (
    <span
      title={status === 'error' && error ? error : undefined}
      className={`inline-flex items-center gap-1 whitespace-nowrap rounded-full border px-2 py-0.5 text-xs font-medium ${conf.cls}`}
    >
      {status === 'processing' && <Loader2 className="h-3 w-3 animate-spin" />}
      {conf.label}
    </span>
  );
}
