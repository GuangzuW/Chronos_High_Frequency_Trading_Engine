'use client';

import React from 'react';
import { useTradeStore } from '@/store/useTradeStore';

const fmt = (n: number, d = 2) =>
  n.toLocaleString(undefined, { minimumFractionDigits: d, maximumFractionDigits: d });

const Positions = () => {
  const { positions } = useTradeStore();
  const open = positions.filter((p) => p.quantity !== 0);

  return (
    <div className="h-full overflow-y-auto custom-scrollbar text-xs font-mono">
      <div className="grid grid-cols-4 text-[10px] uppercase text-gray-500 font-bold sticky top-0 bg-neutral-900 py-1.5 px-2 border-b border-neutral-800">
        <span>Symbol</span><span className="text-right">Qty</span>
        <span className="text-right">Avg</span><span className="text-right">Realized</span>
      </div>
      {open.length === 0 && (
        <div className="text-center text-neutral-700 py-6 italic uppercase tracking-widest text-[10px]">No open positions</div>
      )}
      {open.map((p) => {
        const avg = p.quantity ? p.cost_basis / p.quantity : 0;
        const longShort = p.quantity > 0 ? 'text-green-400' : 'text-red-400';
        return (
          <div key={p.symbol} className="grid grid-cols-4 py-1.5 px-2 border-b border-neutral-800/30 hover:bg-neutral-800/40">
            <span className="text-gray-200 font-bold">{p.symbol}</span>
            <span className={`text-right ${longShort}`}>{fmt(p.quantity, 3)}</span>
            <span className="text-right text-gray-400">{fmt(avg)}</span>
            <span className={`text-right ${p.realized_pnl >= 0 ? 'text-green-400' : 'text-red-400'}`}>
              {fmt(p.realized_pnl)}
            </span>
          </div>
        );
      })}
    </div>
  );
};

export default Positions;
