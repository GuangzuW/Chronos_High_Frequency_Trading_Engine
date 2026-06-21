'use client';

import { useCallback, useEffect, useState } from 'react';
import Link from 'next/link';
import { useTradeStore } from '@/store/useTradeStore';
import { getChain, addOption, type OptionContract, type ComboLeg } from '@/lib/api';
import OptionsChain from '@/components/OptionsChain';
import SpreadBuilder from '@/components/SpreadBuilder';
import GreeksPanel from '@/components/GreeksPanel';

export default function OptionsPage() {
  const { account, selectedSymbol } = useTradeStore();
  const [underlying, setUnderlying] = useState(selectedSymbol || 'AAPL');
  const [contracts, setContracts] = useState<OptionContract[]>([]);
  const [legs, setLegs] = useState<ComboLeg[]>([]);

  // Add-contract form.
  const [cStrike, setCStrike] = useState('150');
  const [cRight, setCRight] = useState<'call' | 'put'>('call');
  const [cExpiry, setCExpiry] = useState('2026-12-18');
  const [msg, setMsg] = useState('');

  const loadChain = useCallback(async () => {
    try { setContracts((await getChain(underlying)).chain); } catch { setContracts([]); }
  }, [underlying]);

  useEffect(() => { loadChain(); }, [loadChain]);

  const createContract = async () => {
    const strike = parseFloat(cStrike);
    const symbol = `${underlying}_${cRight[0].toUpperCase()}${Math.round(strike)}`.slice(0, 8);
    try {
      await addOption({ symbol, underlying, expiry: cExpiry, strike, right: cRight, multiplier: 100 });
      setMsg(`Added ${symbol}`);
      loadChain();
    } catch (e) { setMsg('Error: ' + (e as Error).message); }
  };

  const addLeg = (c: OptionContract) =>
    setLegs((prev) => [...prev, { symbol: c.symbol, side: 'buy', price: 0, quantity: 1 }]);

  const inp = 'bg-neutral-950 border border-neutral-800 rounded px-2 py-1 text-xs text-white outline-none focus:border-blue-500';
  const panel = 'border border-neutral-800 bg-neutral-900/20 rounded-md flex flex-col overflow-hidden';
  const head = 'px-3 py-2 bg-neutral-900/60 border-b border-neutral-800 text-[10px] font-black text-gray-500 uppercase tracking-widest';

  return (
    <main className="h-screen bg-neutral-950 text-gray-100 p-3 font-mono flex flex-col overflow-hidden">
      <header className="border border-neutral-800 bg-neutral-900/40 rounded-md px-4 py-2.5 mb-3 flex items-center gap-6 shrink-0">
        <div className="flex items-center gap-2.5">
          <div className="w-7 h-7 bg-blue-600 rounded flex items-center justify-center font-bold text-base italic">C</div>
          <h1 className="text-lg font-bold text-white tracking-tighter uppercase">Chronos<span className="text-blue-500">_Options</span></h1>
        </div>
        <nav className="flex gap-1 text-[11px]">
          <Link href="/" className="px-3 py-1 rounded text-gray-400 hover:bg-neutral-800">Trade</Link>
          <span className="px-3 py-1 rounded bg-blue-600 text-white font-bold">Options</span>
          <Link href="/compliance" className="px-3 py-1 rounded text-gray-400 hover:bg-neutral-800">Compliance</Link>
        </nav>
        <div className="flex items-center gap-2 ml-4">
          <label className="text-[10px] text-gray-500 uppercase font-bold">Underlying</label>
          <input value={underlying} onChange={(e) => setUnderlying(e.target.value.toUpperCase())} className={`${inp} w-24`} />
          <button onClick={loadChain} className="px-3 py-1 rounded bg-neutral-800 hover:bg-neutral-700 text-[10px] font-bold uppercase">Load</button>
        </div>
        <div className="ml-auto text-[11px] text-gray-500">Account: <span className="text-gray-200">{account}</span></div>
      </header>

      <div className="grid grid-cols-12 gap-3 flex-1 min-h-0">
        {/* Chain */}
        <div className={`col-span-6 ${panel}`}>
          <div className={head}>Options Chain · {underlying}</div>
          <div className="flex-1 min-h-0 overflow-hidden">
            <OptionsChain contracts={contracts} onPick={addLeg} />
          </div>
          <div className="border-t border-neutral-800 p-3 flex items-end gap-2 flex-wrap">
            <div><label className="text-[9px] text-gray-500 uppercase font-bold">Strike</label>
              <input value={cStrike} onChange={(e) => setCStrike(e.target.value)} className={`${inp} w-20 block`} /></div>
            <div><label className="text-[9px] text-gray-500 uppercase font-bold">Right</label>
              <select value={cRight} onChange={(e) => setCRight(e.target.value as 'call' | 'put')} className={`${inp} block`}>
                <option value="call">Call</option><option value="put">Put</option></select></div>
            <div><label className="text-[9px] text-gray-500 uppercase font-bold">Expiry</label>
              <input value={cExpiry} onChange={(e) => setCExpiry(e.target.value)} className={`${inp} w-28 block`} /></div>
            <button onClick={createContract} className="px-3 py-1.5 rounded bg-neutral-800 hover:bg-neutral-700 text-[10px] font-bold uppercase">Add Contract</button>
            {msg && <span className="text-[10px] text-gray-400">{msg}</span>}
          </div>
        </div>

        {/* Right: spread builder + greeks */}
        <div className="col-span-6 flex flex-col gap-3 min-h-0">
          <div className={`${panel} flex-1`}>
            <div className={head}>Spread Builder</div>
            <div className="flex-1 min-h-0 overflow-y-auto custom-scrollbar">
              <SpreadBuilder account={account} legs={legs} setLegs={setLegs} />
            </div>
          </div>
          <div className={`${panel} flex-1`}>
            <div className={head}>Position Greeks</div>
            <div className="flex-1 min-h-0"><GreeksPanel /></div>
          </div>
        </div>
      </div>
    </main>
  );
}
