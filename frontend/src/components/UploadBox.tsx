// 上传区：拖拽或点击选择文件，逐个调用上传接口，聚合展示成功数量与失败原因
import { useRef, useState, type ChangeEvent, type DragEvent } from 'react';
import { Loader2, UploadCloud } from 'lucide-react';
import { uploadDocument } from '../api';

const ACCEPT_EXTS = ['.pdf', '.docx', '.md', '.txt', '.json'];
const MAX_BYTES = 20 * 1024 * 1024; // 与后端 max_upload_mb=20 对齐

interface UploadBoxProps {
  /** 任一文件处理完毕后回调（无论成败），用于刷新列表 */
  onUploaded: () => void;
}

export default function UploadBox({ onUploaded }: UploadBoxProps) {
  const [dragging, setDragging] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [notice, setNotice] = useState<{ ok: number; fail: string[] } | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const handleFiles = async (files: FileList | File[]) => {
    if (uploading) return;
    const list = Array.from(files);
    if (list.length === 0) return;

    setUploading(true);
    setNotice(null);
    let ok = 0;
    const fails: string[] = [];

    for (const file of list) {
      const dot = file.name.lastIndexOf('.');
      const ext = dot >= 0 ? file.name.slice(dot).toLowerCase() : '';
      if (!ACCEPT_EXTS.includes(ext)) {
        fails.push(`${file.name}：不支持的格式（仅支持 pdf / docx / md / txt / json）`);
        continue;
      }
      if (file.size > MAX_BYTES) {
        fails.push(`${file.name}：超过 20MB 上限`);
        continue;
      }
      try {
        await uploadDocument(file);
        ok += 1;
      } catch (err) {
        fails.push(`${file.name}：${(err as Error).message}`);
      }
    }

    setUploading(false);
    setNotice({ ok, fail: fails });
    onUploaded();
  };

  const onDrop = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setDragging(false);
    void handleFiles(e.dataTransfer.files);
  };

  const onPick = (e: ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) void handleFiles(e.target.files);
    e.target.value = ''; // 允许重复选择同一文件
  };

  return (
    <div>
      <div
        onClick={() => inputRef.current?.click()}
        onDragOver={(e) => {
          e.preventDefault();
          setDragging(true);
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={onDrop}
        className={`flex cursor-pointer flex-col items-center justify-center rounded-xl border-2 border-dashed px-6 py-10 text-center transition-colors ${
          dragging
            ? 'border-sakura bg-blush'
            : 'border-hairline bg-card hover:border-sakura/60 hover:bg-panel'
        }`}
      >
        <span className="mb-3 flex h-12 w-12 items-center justify-center rounded-full bg-blush text-sakura">
          {uploading ? <Loader2 className="h-5 w-5 animate-spin" /> : <UploadCloud className="h-5 w-5" />}
        </span>
        <p className="text-sm font-medium text-ink-soft">
          {uploading ? '正在上传…' : '拖拽文件到此处，或点击选择文件'}
        </p>
        <p className="mt-1 text-xs text-ink-faint">
          支持 PDF / Word / Markdown / TXT / JSON，单个文件不超过 20MB
        </p>
        <input
          ref={inputRef}
          type="file"
          multiple
          accept={ACCEPT_EXTS.join(',')}
          className="hidden"
          onChange={onPick}
        />
      </div>

      {notice && (notice.ok > 0 || notice.fail.length > 0) && (
        <div className="mt-3 space-y-1.5 text-sm">
          {notice.ok > 0 && (
            <p className="rounded-lg border border-success-bg bg-success-bg px-3 py-2 text-success-fg">
              成功上传 {notice.ok} 个文档，正在后台解析入库。
            </p>
          )}
          {notice.fail.map((msg, i) => (
            <p
              key={i}
              className="rounded-lg border border-bad-bg bg-bad-bg px-3 py-2 text-bad-fg"
            >
              {msg}
            </p>
          ))}
        </div>
      )}
    </div>
  );
}
