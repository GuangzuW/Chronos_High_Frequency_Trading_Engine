'use client';

import React, { useMemo } from 'react';
import type { OptionContract } from '@/lib/api';

const fmt = (n?: number) => (n == null ? '--' : n.toFixed(2));

// Groups option contracts into an expiry -> strike grid with call/put columns.
const OptionsChain = ({ contracts, onPick }:
  { contracts: OptionContract[]; onPick: (c: OptionContract) => void }) => {
  const groups = useMemo(() => {
    const byExpiry = new Map<string, Map<number, { call?: OptionContract; put?: OptionContract }>>();
    for (const c of contracts) {
      if (c.kind !== 'option' || c.strike == null || !c.expiry) continue;
      if (!byExpiry.has(c.expiry)) byExpiry.set(c.expiry, new Map());
      const strikes = byExpiry.get(c.expiry)!;
      if (!strikes.has(c.strike)) strikes.set(c.strike, {});
      const cell = strikes.get(c.strike)!;
      if (c.right === 'call') cell.call = c; else cell.put = c;
    }
    return [...byExpiry.entries()].sort((a, z) => a[0].localeCompare(z[0]));
  }, [contracts]);

  if (groups.length === 0) {
    return <div className="text-center text-neutral-700 italic uppercase tracking-widest text-[10px] py-8">No option contracts — add some below</div>;
  }

  const cell = (c?: OptionContract, side: 'call' | 'put' = 'call') => (
    <button disabled={!c} onClick={() => c && onPick(c)}
      className={`flex-1 text-[11px] py-1.5 rounded transition-colors font-mono ${c ? 'hover:bg-neutral-800 text-gray-200 cursor-pointer' : 'text-neutral-700 cursor-default'} ${side === 'call' ? 'text-right pr-3' : 'text-left pl-3'}`}>
      {c ? c.symbol : '·'}
    </button>
  );

  return (
    <div className="overflow-y-auto custom-scrollbar text-xs font-mono">
      {groups.map(([expiry, strikes]) => (
        <div key={expiry} className="mb-3">
          <div className="text-[10px] uppercase text-blue-400 font-bold tracking-wider px-2 py-1 sticky top-0 bg-neutral-900 border-b border-neutral-800">
            Expiry {expiry}
          </div>
          <div className="grid grid-cols-[1fr_70px_1fr] text-[9px] uppercase text-gray-500 font-bold px-2 py-1">
            <span className="text-right pr-3">Calls</span><span className="text-center">Strike</span><span className="pl-3">Puts</span>
          </div>
          {[...strikes.entries()].sort((a, z) => a[0] - z[0]).map(([strike, cp]) => (
            <div key={strike} className="grid grid-cols-[1fr_70px_1fr] items-center border-b border-neutral-800/30 hover:bg-neutral-800/20">
              {cell(cp.call, 'call')}
              <span className="text-center text-gray-100 font-bold">{fmt(strike)}</span>
              {cell(cp.put, 'put')}
            </div>
          ))}
        </div>
      ))}
    </div>
  );
};

export default OptionsChain;
