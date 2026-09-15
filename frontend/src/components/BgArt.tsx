/**
 * 正文区背景美图（移植自「音阅」）：右下角定置、向左淡出，压低存在感但不失存在性。
 * 樱花 → /bg/sakura.webp，未来 → /bg/miku.webp，素笺无背景图。
 * 素材缺失时不渲染。滚动正文时保持定置（挂在布局层，不随内容滚动）。
 */
import { useEffect, useState } from 'react';
import { useTheme, type ThemeName } from '../theme';

const BG_ART: Partial<Record<ThemeName, string>> = {
  sakura: '/bg/sakura.webp',
  miku: '/bg/miku.webp',
};

export default function BgArt() {
  const theme = useTheme();
  const src = BG_ART[theme];
  const [ok, setOk] = useState(false);

  useEffect(() => {
    setOk(false);
    if (!src) return;
    let alive = true;
    const el = new window.Image();
    el.onload = () => alive && setOk(true);
    el.onerror = () => {};
    el.src = src;
    return () => {
      alive = false;
    };
  }, [src]);

  if (!src || !ok) return null;
  return (
    <div aria-hidden className="pointer-events-none fixed inset-0 z-0 overflow-hidden">
      <img
        src={src}
        alt=""
        draggable={false}
        className="absolute bottom-0 right-0 h-[75%] max-w-none opacity-35 [mask-image:linear-gradient(to_left,black_40%,transparent_95%)]"
      />
    </div>
  );
}
