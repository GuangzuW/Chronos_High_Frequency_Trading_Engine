'use client';

import React, { useState } from 'react';
import { placeCombo, type ComboLeg } from '@/lib/api';

// Multi-leg (spread) order builder -> atomic /combos submission.
const SpreadBuilder = ({ account, legs, setLegs, onSubmitted }:
  {
    account: string;
    legs: ComboLeg[];
    setLegs: (l: ComboLeg[]) => void;
    onSubmitted?: () => void;
  }) => {
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState('');

  const update = (i: number, patch: Partial<ComboLeg>) =>
    setLegs(legs.map((l, idx) => (idx === i ? { ...l, ...patch } : l)));
  const remove = (i: number) => setLegs(legs.filter((_, idx) => idx !== i));

  const submit = async () => {
    if (legs.length === 0) return;
    setBusy(true); setMsg('');
    try {
      const res = await placeCombo(account, legs.map((l) => ({
        symbol: l.symbol, side: l.side, price: Number(l.price), quantity: Number(l.quantity),
      })));
      setMsg(res.status === 'filled'
        ? `Filled ${res.legs.length} legs (#${res.legs.join(', #')})`
        : `Rejected: ${res.reason ?? 'unknown'}`);
      if (res.status === 'filled') { setLegs([]); onSubmitted?.(); }
    } catch (e) { setMsg('Error: ' + (e as Error).message); }
    finally { setBusy(false); }
  };

  const inp = 'w-full bg-neutral-950 border border-neutral-800 rounded px-1.5 py-1 text-xs text-white outline-none focus:border-blue-500';

  return (
    <div className="p-3 text-xs font-mono">
      <div className="text-[10px] uppercase text-gray-500 font-bold mb-2">Spread Builder · {account}</div>
      {legs.length === 0 && (
        <div className="text-neutral-700 italic text-[10px] py-3">Click contracts in the chain to add legs.</div>
      )}
      <div className="space-y-1.5">
        {legs.map((l, i) => (
          <div key={i} className="grid grid-cols-[1fr_64px_70px_56px_24px] gap-1 items-center">
            <span className="text-gray-200 truncate">{l.symbol}</span>
            <select value={l.side} onChange={(e) => update(i, { side: e.target.value as 'buy' | 'sell' })}
              className={`${inp} ${l.side === 'buy' ? 'text-green-400' : 'text-red-400'}`}>
              <option value="buy">Buy</option><option value="sell">Sell</option>
            </select>
            <input type="number" placeholder="price" value={l.price || ''}
              onChange={(e) => update(i, { price: parseFloat(e.target.value) })} className={inp} />
            <input type="number" placeholder="qty" value={l.quantity || ''}
              onChange={(e) => update(i, { quantity: parseFloat(e.target.value) })} className={inp} />
            <button onClick={() => remove(i)} className="text-gray-500 hover:text-red-400">✕</button>
          </div>
        ))}
      </div>
      {legs.length > 0 && (
        <button onClick={submit} disabled={busy}
          className="w-full mt-3 py-2 rounded bg-blue-600 hover:bg-blue-500 text-white text-[11px] font-black uppercase">
          {busy ? 'Submitting…' : `Submit ${legs.length}-Leg Combo`}
        </button>
      )}
      {msg && <div className="text-[10px] text-gray-400 mt-2 break-words">{msg}</div>}
    </div>
  );
};

export default SpreadBuilder;
