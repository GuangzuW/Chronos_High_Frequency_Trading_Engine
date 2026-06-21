'use client';

import React, { useEffect, useMemo, useState } from 'react';
import { useTradeStore } from '@/store/useTradeStore';
import { getCashflow, type CashflowPoint } from '@/lib/api';

const money = (n: number) => n.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 });

// Account cash-balance curve over the ledger event sequence (with net-of-funding stat).
const CashCurve = () => {
  const { account } = useTradeStore();
  const [pts, setPts] = useState<CashflowPoint[]>([]);
  const [meta, setMeta] = useState({ funded: 0, ending: 0, net: 0 });

  useEffect(() => {
    let alive = true;
    const load = async () => {
      try {
        const cf = await getCashflow(account);
        if (alive) { setPts(cf.series); setMeta({ funded: cf.funded, ending: cf.ending_cash, net: cf.net_ex_funding }); }
      } catch { /* not funded yet */ }
    };
    load();
    const t = setInterval(load, 2500);
    return () => { alive = false; clearInterval(t); };
  }, [account]);

  const path = useMemo(() => {
    if (pts.length < 2) return '';
    const vals = pts.map((p) => p.balance);
    const lo = Math.min(...vals), hi = Math.max(...vals), rng = hi - lo || 1;
    return pts.map((p, i) => {
      const x = (i / (pts.length - 1)) * 100;
      const y = 100 - ((p.balance - lo) / rng) * 96 - 2;
      return `${x.toFixed(2)},${y.toFixed(2)}`;
    }).join(' ');
  }, [pts]);

  const up = meta.net >= 0;

  return (
    <div className="h-full flex flex-col p-3 text-xs font-mono">
      <div className="grid grid-cols-3 gap-2 mb-2">
        <Cell label="Cash" value={`$${money(meta.ending)}`} />
        <Cell label="Funded" value={`$${money(meta.funded)}`} muted />
        <Cell label="Net (ex-fund)" value={`$${money(meta.net)}`} pnl={meta.net} />
      </div>
      <div className="flex-1 min-h-0">
        {pts.length < 2 ? (
          <div className="h-full flex items-center justify-center text-neutral-700 italic uppercase tracking-widest text-[10px]">
            Trade to build a curve
          </div>
        ) : (
          <svg viewBox="0 0 100 100" preserveAspectRatio="none" className="w-full h-full">
            <polyline points={path} fill="none" stroke={up ? '#27b083' : '#e86349'} strokeWidth="0.8" />
          </svg>
        )}
      </div>
    </div>
  );
};

const Cell = ({ label, value, muted, pnl }: { label: string; value: string; muted?: boolean; pnl?: number }) => {
  const color = pnl != null ? (pnl >= 0 ? 'text-green-400' : 'text-red-400') : muted ? 'text-gray-500' : 'text-gray-100';
  return (
    <div className="bg-neutral-950 border border-neutral-800 rounded px-2 py-1.5">
      <div className="text-[9px] uppercase text-gray-500 font-bold tracking-wide">{label}</div>
      <div className={`text-xs font-bold ${color}`}>{value}</div>
    </div>
  );
};

export default CashCurve;
