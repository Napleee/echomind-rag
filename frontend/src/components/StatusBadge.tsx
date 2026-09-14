// 文档状态徽标：processing 转圈 / ready 绿色 / error 红色（悬停 title 提示错误信息）
import { Loader2 } from 'lucide-react';

interface StatusBadgeProps {
  status: string;
  error?: string | null;
}

const STYLE: Record<string, { label: string; cls: string }> = {
  processing: { label: '处理中', cls: 'border-amber-200 bg-amber-50 text-amber-600' },
  ready: { label: '就绪', cls: 'border-success-bg bg-success-bg text-success-fg' },
  error: { label: '失败', cls: 'border-bad-bg bg-bad-bg text-bad-fg' },
};

export default function StatusBadge({ status, error }: StatusBadgeProps) {
  const conf = STYLE[status] ?? { label: status, cls: 'border-hairline bg-panel text-ink-faint' };
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
