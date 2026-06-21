'use client';

import React, { useState } from 'react';
import { useTradeStore } from '@/store/useTradeStore';
import { positionGreeks, type GreeksResult } from '@/lib/api';

const fmt = (n: number, d = 3) => n.toLocaleString(undefined, { minimumFractionDigits: d, maximumFractionDigits: d });

const GreeksPanel = () => {
  const { account } = useTradeStore();
  const [rate, setRate] = useState('0.05');
  const [vol, setVol] = useState('0.20');
  const [res, setRes] = useState<GreeksResult | null>(null);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState('');

  const compute = async () => {
    setBusy(true); setErr('');
    try {
      // Spots default to each underlying's last trade price on the backend.
      setRes(await positionGreeks(account, { rate: parseFloat(rate), vol: parseFloat(vol) }));
    } catch (e) { setErr((e as Error).message); }
    finally { setBusy(false); }
  };

  const inp = 'w-full bg-neutral-950 border border-neutral-800 rounded px-2 py-1 text-xs text-white outline-none focus:border-blue-500';
  const net = res?.net;

  return (
    <div className="h-full overflow-y-auto custom-scrollbar p-3 text-xs font-mono space-y-3">
      <div className="flex gap-2 items-end">
        <div className="flex-1"><label className="text-[9px] text-gray-500 uppercase font-bold">Rate</label>
          <input className={inp} value={rate} onChange={(e) => setRate(e.target.value)} /></div>
        <div className="flex-1"><label className="text-[9px] text-gray-500 uppercase font-bold">Vol</label>
          <input className={inp} value={vol} onChange={(e) => setVol(e.target.value)} /></div>
        <button onClick={compute} disabled={busy}
          className="px-3 py-1.5 rounded bg-blue-600 hover:bg-blue-500 text-white text-[10px] font-bold uppercase">
          {busy ? '...' : 'Compute'}
        </button>
      </div>

      {err && <div className="text-red-400 text-[10px]">{err}</div>}

      {net && (
        <div className="grid grid-cols-5 gap-1 text-center">
          {(['delta', 'gamma', 'vega', 'theta', 'rho'] as const).map((k) => (
            <div key={k} className="bg-neutral-950 border border-neutral-800 rounded py-1.5">
              <div className="text-[9px] uppercase text-gray-500 font-bold">{k}</div>
              <div className={`text-xs font-bold ${net[k] >= 0 ? 'text-green-400' : 'text-red-400'}`}>{fmt(net[k])}</div>
            </div>
          ))}
        </div>
      )}

      {res && res.positions.length > 0 && (
        <div>
          <div className="grid grid-cols-4 text-[10px] uppercase text-gray-500 font-bold border-b border-neutral-800 py-1">
            <span>Contract</span><span className="text-right">Qty</span>
            <span className="text-right">Δ</span><span className="text-right">Θ</span>
          </div>
          {res.positions.map((p) => (
            <div key={p.symbol} className="grid grid-cols-4 py-1 border-b border-neutral-800/30">
              <span className="text-gray-200">{p.symbol}</span>
              <span className="text-right text-gray-400">{fmt(p.contracts, 0)}</span>
              <span className="text-right text-gray-300">{fmt(p.delta)}</span>
              <span className="text-right text-gray-300">{fmt(p.theta)}</span>
            </div>
          ))}
        </div>
      )}

      {res && res.positions.length === 0 && (
        <div className="text-center text-neutral-700 italic uppercase tracking-widest text-[10px] py-4">
          No option positions
        </div>
      )}
    </div>
  );
};

export default GreeksPanel;
