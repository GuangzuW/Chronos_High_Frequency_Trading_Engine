'use client';

import React, { useEffect, useState } from 'react';
import { useTradeStore } from '@/store/useTradeStore';
import { getMarkets, type MarketRow } from '@/lib/api';

const fmt = (n: number | null) =>
  n == null ? '--' : n.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 });

const Watchlist = () => {
  const { selectedSymbol, setSelectedSymbol } = useTradeStore();
  const [rows, setRows] = useState<MarketRow[]>([]);

  useEffect(() => {
    let alive = true;
    const load = async () => {
      try { const r = await getMarkets(); if (alive) setRows(r.markets); } catch { /* backend down */ }
    };
    load();
    const t = setInterval(load, 1500);
    return () => { alive = false; clearInterval(t); };
  }, []);

  return (
    <div className="h-full overflow-y-auto custom-scrollbar text-xs font-mono">
      <div className="grid grid-cols-4 text-[10px] uppercase text-gray-500 font-bold sticky top-0 bg-neutral-900 px-2 py-1.5 border-b border-neutral-800">
        <span>Symbol</span><span className="text-right">Bid</span><span className="text-right">Ask</span><span className="text-right">Last</span>
      </div>
      {rows.length === 0 && (
        <div className="text-center text-neutral-700 italic uppercase tracking-widest text-[10px] py-4">No instruments</div>
      )}
      {rows.map((m) => (
        <button key={m.symbol} onClick={() => setSelectedSymbol(m.symbol)}
          className={`w-full grid grid-cols-4 px-2 py-1.5 border-b border-neutral-800/30 transition-colors text-left ${m.symbol === selectedSymbol ? 'bg-blue-600/15' : 'hover:bg-neutral-800/40'}`}>
          <span className={`font-bold ${m.symbol === selectedSymbol ? 'text-blue-400' : 'text-gray-200'}`}>
            {m.symbol}{m.kind === 'option' ? <span className="text-gray-600 text-[9px]"> opt</span> : ''}
          </span>
          <span className="text-right text-green-400">{fmt(m.best_bid)}</span>
          <span className="text-right text-red-400">{fmt(m.best_ask)}</span>
          <span className="text-right text-gray-100">{fmt(m.last)}</span>
        </button>
      ))}
    </div>
  );
};

export default Watchlist;
