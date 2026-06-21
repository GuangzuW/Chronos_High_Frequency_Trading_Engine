'use client';

import React, { useMemo } from 'react';
import { useTradeStore } from '@/store/useTradeStore';

// Cumulative depth (market-depth) chart rendered as an SVG area, built from the book.
const DepthChart = () => {
  const { bids, asks } = useTradeStore();

  const { bidPts, askPts, maxCum, lo, hi } = useMemo(() => {
    const b = [...bids].sort((a, z) => z.price - a.price); // high -> low
    const a = [...asks].sort((x, z) => x.price - z.price);  // low -> high
    let cb = 0; const bidCum = b.map((l) => ({ price: l.price, cum: (cb += l.quantity) }));
    let ca = 0; const askCum = a.map((l) => ({ price: l.price, cum: (ca += l.quantity) }));
    const maxCum = Math.max(cb, ca, 1);
    const prices = [...bidCum, ...askCum].map((p) => p.price);
    const lo = prices.length ? Math.min(...prices) : 0;
    const hi = prices.length ? Math.max(...prices) : 1;
    return { bidPts: bidCum, askPts: askCum, maxCum, lo, hi };
  }, [bids, asks]);

  const W = 100, H = 100;
  const x = (price: number) => (hi === lo ? 50 : ((price - lo) / (hi - lo)) * W);
  const y = (cum: number) => H - (cum / maxCum) * H;

  const path = (pts: { price: number; cum: number }[], side: 'bid' | 'ask') => {
    if (pts.length === 0) return '';
    const ordered = side === 'bid' ? [...pts].reverse() : pts; // left->right by price
    const line = ordered.map((p) => `${x(p.price).toFixed(2)},${y(p.cum).toFixed(2)}`);
    const first = ordered[0], last = ordered[ordered.length - 1];
    return `M ${x(first.price).toFixed(2)},${H} L ${line.join(' L ')} L ${x(last.price).toFixed(2)},${H} Z`;
  };

  const empty = bidPts.length === 0 && askPts.length === 0;

  return (
    <div className="h-full w-full p-2">
      {empty ? (
        <div className="h-full flex items-center justify-center text-neutral-700 italic uppercase tracking-widest text-[10px]">
          No book depth
        </div>
      ) : (
        <svg viewBox="0 0 100 100" preserveAspectRatio="none" className="w-full h-full">
          <path d={path(bidPts, 'bid')} fill="rgba(39,176,131,0.18)" stroke="#27b083" strokeWidth="0.6" />
          <path d={path(askPts, 'ask')} fill="rgba(232,99,73,0.18)" stroke="#e86349" strokeWidth="0.6" />
        </svg>
      )}
    </div>
  );
};

export default DepthChart;
