/**
 * 主题装饰（移植自「音阅」）：顶边挂件（原创 SVG，摇摆）+ 飘落花瓣层。
 * 所有位置/时长都是固定值 —— 不用随机数，避免渲染不一致。
 * 纯 CSS/SVG 原创图形，无版权素材。
 * 挂件在樱花/未来主题渲染（颜色走 --charm-* 变量），素笺主题整体隐藏；
 * 花瓣仅樱花主题（粉色与蓝青系不搭）。
 * 挂件形状在音阅的爱心/星星/音符/磁带基础上换成书页/气泡——契合知识库气质。
 */
import type { CSSProperties, ReactNode } from 'react';
import { useTheme } from '../theme';

type Shape = 'heart' | 'star' | 'book' | 'bubble';

const SHAPE_SVG: Record<Shape, ReactNode> = {
  heart: (
    <path
      d="M12 20.5C7 16.5 3.5 13.2 3.5 9.6 3.5 7 5.5 5 8 5c1.6 0 3.1.8 4 2.1C12.9 5.8 14.4 5 16 5c2.5 0 4.5 2 4.5 4.6 0 3.6-3.5 6.9-8.5 10.9Z"
      fill="var(--charm-soft)"
      stroke="var(--charm-strong)"
      strokeWidth="1.4"
    />
  ),
  star: (
    <path
      d="M12 3.5l2.6 5.3 5.9.9-4.3 4.1 1 5.8L12 16.9l-5.2 2.7 1-5.8-4.3-4.1 5.9-.9L12 3.5Z"
      fill="#fde9b8"
      stroke="#e8b93c"
      strokeWidth="1.4"
    />
  ),
  book: (
    <>
      <path
        d="M12 6.5C10 4.8 7.3 4.4 4 5v13.5c3.3-.6 6-.2 8 1.5 2-1.7 4.7-2.1 8-1.5V5c-3.3-.6-6-.2-8 1.5Z"
        fill="var(--charm-soft)"
        stroke="var(--charm-strong)"
        strokeWidth="1.4"
        strokeLinejoin="round"
      />
      <path d="M12 6.5V20" stroke="var(--charm-strong)" strokeWidth="1.2" />
    </>
  ),
  bubble: (
    <>
      <path
        d="M4.5 7.5A2 2 0 0 1 6.5 5.5h11a2 2 0 0 1 2 2v6a2 2 0 0 1-2 2H10l-4 3.5v-3.6a2 2 0 0 1-1.5-1.9Z"
        fill="var(--charm-soft)"
        stroke="var(--charm-strong)"
        strokeWidth="1.4"
        strokeLinejoin="round"
      />
      <circle cx="9" cy="10.5" r="1" fill="var(--charm-strong)" />
      <circle cx="12.5" cy="10.5" r="1" fill="var(--charm-strong)" />
      <circle cx="16" cy="10.5" r="1" fill="var(--charm-strong)" />
    </>
  ),
};

interface CharmItem {
  shape: Shape;
  left: string; // 距左边缘
  rope: number; // 挂绳长度 px
  delay: number; // 摇摆相位错开
  duration: number;
}

const DEFAULT_CHARMS: CharmItem[] = [
  { shape: 'star', left: '6%', rope: 14, delay: 0, duration: 4.2 },
  { shape: 'heart', left: '30%', rope: 26, delay: 0.9, duration: 3.6 },
  { shape: 'book', left: '58%', rope: 10, delay: 1.6, duration: 4.6 },
  { shape: 'bubble', left: '84%', rope: 20, delay: 0.4, duration: 3.9 },
];

/** 一排挂在容器下边缘、向正文区垂落的小挂件。容器需 relative，挂件不响应鼠标。 */
export function Charms({ items = DEFAULT_CHARMS }: { items?: CharmItem[] }) {
  const theme = useTheme();
  if (theme !== 'sakura' && theme !== 'miku') return null;
  return (
    <div className="pointer-events-none absolute inset-x-0 top-full z-10 hidden h-0 md:block" aria-hidden>
      {items.map((c) => (
        <div
          key={c.shape}
          className="charm absolute top-0 flex flex-col items-center"
          style={{ left: c.left, animationDelay: `${c.delay}s`, animationDuration: `${c.duration}s` }}
        >
          <div
            className="w-px"
            style={{
              height: c.rope,
              backgroundColor: 'color-mix(in srgb, var(--charm-strong) 40%, transparent)',
            }}
          />
          <svg width={24} height={24} viewBox="0 0 24 24">
            {SHAPE_SVG[c.shape]}
          </svg>
        </div>
      ))}
    </div>
  );
}

const PETALS = [
  { left: '6vw', size: 13, duration: 16, delay: 0, drift: '6vw', opacity: 0.35 },
  { left: '18vw', size: 9, duration: 22, delay: 5, drift: '-4vw', opacity: 0.25 },
  { left: '31vw', size: 15, duration: 19, delay: 11, drift: '8vw', opacity: 0.3 },
  { left: '47vw', size: 8, duration: 25, delay: 2, drift: '-6vw', opacity: 0.22 },
  { left: '62vw', size: 12, duration: 17, delay: 8, drift: '5vw', opacity: 0.32 },
  { left: '76vw', size: 10, duration: 23, delay: 14, drift: '-5vw', opacity: 0.26 },
  { left: '90vw', size: 14, duration: 20, delay: 4, drift: '7vw', opacity: 0.3 },
];

function PetalPath({ size }: { size: number }) {
  // 花瓣：带缺口的水滴形，粉色渐变
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" style={{ display: 'block' }}>
      <path d="M12 2C17 6 21 10 21 15a9 9 0 0 1-18 0C3 10 7 6 12 2Z" fill="#f9b8cd" />
      <path d="M12 4C13 9 13 14 12 20" stroke="#f28bac" strokeWidth="1.2" fill="none" />
    </svg>
  );
}

/** 全屏花瓣层：固定定位、不响应鼠标，放在应用最底层。 */
export function Petals() {
  const theme = useTheme();
  if (theme !== 'sakura') return null;
  return (
    <div className="pointer-events-none fixed inset-0 z-0 overflow-hidden" aria-hidden>
      {PETALS.map((p, i) => (
        <div
          key={i}
          className="petal"
          style={
            {
              left: p.left,
              animationDuration: `${p.duration}s`,
              animationDelay: `${p.delay}s`,
              '--petal-drift': p.drift,
              '--petal-opacity': p.opacity,
            } as CSSProperties
          }
        >
          <PetalPath size={p.size} />
        </div>
      ))}
    </div>
  );
}
