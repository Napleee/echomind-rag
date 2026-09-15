/**
 * 看板娘（移植自「音阅」）：各主题独立的角色素材（透明底 PNG）。
 *   樱花 → public/mascot/{idle,listening}.png（原创角色）
 *   未来 → public/miku/{idle,listening}.png（初音未来二创，遵循 Piapro Character License，非商业使用）
 * 素笺主题无角色。素材未就绪时显示 fallback，界面依旧成立。
 * 与音阅的 idle/listening 对应这里的 idle/active（回答中）。
 */
import { useEffect, useState, type ReactNode } from 'react';
import { useTheme, type ThemeName } from '../theme';

const ASSET_BASE: Partial<Record<ThemeName, string>> = {
  sakura: '/mascot',
  miku: '/miku',
};

export default function Mascot({
  size = 120,
  className = '',
  active = false,
  fallback = null,
}: {
  size?: number;
  className?: string;
  /** 回答中 = 音阅的 listening 素材 + 点头动画 */
  active?: boolean;
  fallback?: ReactNode;
}) {
  const theme = useTheme();
  const [ready, setReady] = useState<Set<string>>(new Set());
  const base = ASSET_BASE[theme];
  const src = base ? `${base}/${active ? 'listening' : 'idle'}.png` : '';

  // 探测素材是否存在，不存在则降级
  useEffect(() => {
    if (!src || ready.has(src)) return;
    let alive = true;
    const el = new window.Image();
    el.onload = () => alive && setReady((s) => new Set(s).add(src));
    el.onerror = () => {};
    el.src = src;
    return () => {
      alive = false;
    };
  }, [src, ready]);

  if (!base || !ready.has(src)) return <>{fallback}</>;

  return (
    <img
      src={src}
      alt="看板娘"
      width={size}
      height={size}
      className={`${className} ${active ? 'mascot-active' : ''}`}
      draggable={false}
    />
  );
}
