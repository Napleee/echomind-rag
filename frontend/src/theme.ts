/**
 * 主题状态：sakura（樱花）| paper（素笺）| miku（未来）。
 * 移植自「音阅」的 theme store（zustand → 极简 useSyncExternalStore 实现，零依赖）。
 * 切换 = 改 <html> 的 data-theme 属性，CSS 变量实时解析，无需重载。
 * 首帧由 index.html 里的内联脚本提前设置，避免闪屏；本模块负责后续切换与持久化。
 */
import { useSyncExternalStore } from 'react';

export type ThemeName = 'sakura' | 'paper' | 'miku';

/** 切换器渲染用：[值, 中文标签] */
export const THEMES: [ThemeName, string][] = [
  ['sakura', '樱花'],
  ['paper', '素笺'],
  ['miku', '未来'],
];

const KEY = 'echomind-theme';

let current: ThemeName = 'sakura';
const listeners = new Set<() => void>();

function emit() {
  listeners.forEach((l) => l());
}

export function setTheme(theme: ThemeName) {
  current = theme;
  document.documentElement.dataset.theme = theme;
  try {
    localStorage.setItem(KEY, theme);
  } catch {
    /* 隐私模式等场景下持久化失败可忽略 */
  }
  emit();
}

/** 应用挂载后调用：把 localStorage 里的选择同步进 store 与 DOM。 */
export function initTheme() {
  try {
    const t = localStorage.getItem(KEY) as ThemeName | null;
    if (t && THEMES.some(([v]) => v === t)) {
      current = t;
      document.documentElement.dataset.theme = t;
      emit();
    }
  } catch {
    /* 同上 */
  }
}

export function useTheme(): ThemeName {
  return useSyncExternalStore(
    (l) => {
      listeners.add(l);
      return () => listeners.delete(l);
    },
    () => current,
    () => current,
  );
}
