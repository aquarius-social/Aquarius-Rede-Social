import type { CSSProperties } from 'react';

export type IconName =
  | 'grid' | 'pipe' | 'list' | 'star' | 'eye' | 'shield' | 'spark' | 'users'
  | 'trend' | 'globe' | 'flag' | 'lock' | 'gear' | 'cal' | 'download' | 'chevR'
  | 'menu' | 'sun' | 'moon' | 'search' | 'bell' | 'check' | 'x'
  | 'alert' | 'sync' | 'pause' | 'dots' | 'trash' | 'send' | 'plus' | 'doc';

const P: Record<IconName, string> = {
  grid: 'M3 3h7v7H3zM14 3h7v7h-7zM14 14h7v7h-7zM3 14h7v7H3z',
  pipe: 'M3 12h4l3-7 4 14 3-7h4',
  list: 'M8 6h13M8 12h13M8 18h13M3 6h.01M3 12h.01M3 18h.01',
  star: 'M12 3l2.9 6.3 6.6.6-5 4.4 1.5 6.5L12 18l-6 3.3 1.5-6.5-5-4.4 6.6-.6z',
  eye: 'M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7-10-7-10-7z M12 15a3 3 0 100-6 3 3 0 000 6z',
  shield: 'M12 3l8 3v6c0 5-3.5 8-8 9-4.5-1-8-4-8-9V6z',
  spark: 'M12 3v3M12 18v3M3 12h3M18 12h3M5.6 5.6l2.1 2.1M16.3 16.3l2.1 2.1M5.6 18.4l2.1-2.1M16.3 7.7l2.1-2.1',
  users: 'M9 8a3.5 3.5 0 100-7 3.5 3.5 0 000 7zM3 21v-1a6 6 0 0112 0v1M17 11a3 3 0 100-6M22 21v-1a6 6 0 00-5-5.9',
  trend: 'M3 17l6-6 4 4 8-8M21 7v5M21 7h-5',
  globe: 'M12 21a9 9 0 100-18 9 9 0 000 18zM3 12h18M12 3c2.5 2.5 3.5 6 3.5 9s-1 6.5-3.5 9c-2.5-2.5-3.5-6-3.5-9s1-6.5 3.5-9z',
  flag: 'M4 21V4M4 4h13l-2 4 2 4H4',
  lock: 'M6 11V8a6 6 0 1112 0v3M5 11h14v10H5z',
  gear: 'M12 15a3 3 0 100-6 3 3 0 000 6zM19.4 15a1.65 1.65 0 00.33 1.82l.06.06a2 2 0 11-2.83 2.83l-.06-.06a1.65 1.65 0 00-1.82-.33 1.65 1.65 0 00-1 1.51V21a2 2 0 01-4 0v-.09A1.65 1.65 0 009 19.4a1.65 1.65 0 00-1.82.33l-.06.06a2 2 0 11-2.83-2.83l.06-.06a1.65 1.65 0 00.33-1.82 1.65 1.65 0 00-1.51-1H3a2 2 0 010-4h.09A1.65 1.65 0 004.6 9a1.65 1.65 0 00-.33-1.82l-.06-.06a2 2 0 112.83-2.83l.06.06A1.65 1.65 0 009 4.6a1.65 1.65 0 001-1.51V3a2 2 0 014 0v.09a1.65 1.65 0 001 1.51 1.65 1.65 0 001.82-.33l.06-.06a2 2 0 112.83 2.83l-.06.06a1.65 1.65 0 00-.33 1.82V9a1.65 1.65 0 001.51 1H21a2 2 0 010 4h-.09a1.65 1.65 0 00-1.51 1z',
  cal: 'M3 5h18v16H3zM8 3v4M16 3v4M3 11h18',
  download: 'M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4M7 10l5 5 5-5M12 15V3',
  chevR: 'M9 6l6 6-6 6',
  menu: 'M3 6h18M3 12h18M3 18h18',
  sun: 'M12 17a5 5 0 100-10 5 5 0 000 10zM12 1v2M12 21v2M4.2 4.2l1.4 1.4M18.4 18.4l1.4 1.4M1 12h2M21 12h2M4.2 19.8l1.4-1.4M18.4 5.6l1.4-1.4',
  moon: 'M21 12.8A9 9 0 1111.2 3a7 7 0 009.8 9.8z',
  search: 'M11 18a7 7 0 100-14 7 7 0 000 14zM20 20l-4.3-4.3',
  bell: 'M18 8a6 6 0 00-12 0c0 7-3 9-3 9h18s-3-2-3-9M13.7 21a2 2 0 01-3.4 0',
  check: 'M5 12l4 4 10-10',
  x: 'M6 6l12 12M18 6L6 18',
  alert: 'M12 3 22 20H2zM12 10v4M12 17.5v.5',
  sync: 'M23 4v6h-6M1 20v-6h6M3.5 9a9 9 0 0 1 14.9-3.4L23 10M1 14l4.6 4.4A9 9 0 0 0 20.5 15',
  pause: 'M8 5v14M16 5v14',
  dots: 'M5 12h.01M12 12h.01M19 12h.01',
  trash: 'M3 6h18M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2',
  send: 'M22 2 11 13M22 2l-7 20-4-9-9-4 20-7z',
  plus: 'M12 5v14M5 12h14',
  doc: 'M14 3H6a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V9zM14 3v6h6M8 13h8M8 17h5',
};

export function Icon({ name, size = 18, color = 'currentColor', stroke = 2, style }: {
  name: IconName; size?: number; color?: string; stroke?: number; style?: CSSProperties;
}) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke={color}
      strokeWidth={stroke} strokeLinecap="round" strokeLinejoin="round" style={style}>
      <path d={P[name]} />
    </svg>
  );
}
