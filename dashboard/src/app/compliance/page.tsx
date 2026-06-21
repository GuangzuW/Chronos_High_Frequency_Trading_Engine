'use client';

import { useCallback, useEffect, useState } from 'react';
import Link from 'next/link';
import { useTradeStore } from '@/store/useTradeStore';
import { getStatement, getSurveillance, type Statement } from '@/lib/api';

type Surveil = Awaited<ReturnType<typeof getSurveillance>>;
const cents = (n: number) => (n / 100).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 });
const qty = (n: number) => (n / 1000).toLocaleString(undefined, { maximumFractionDigits: 3 });
const px = (n: number) => (n / 100).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 });

export default function CompliancePage() {
  const { account, setAccount } = useTradeStore();
  const [stmt, setStmt] = useState<Statement | null>(null);
  const [surveil, setSurveil] = useState<Surveil | null>(null);

  const load = useCallback(async () => {
    try { setStmt(await getStatement(account)); } catch { setStmt(null); }
    try { setSurveil(await getSurveillance()); } catch { setSurveil(null); }
  }, [account]);

  useEffect(() => { load(); }, [load]);

  const panel = 'border border-neutral-800 bg-neutral-900/20 rounded-md flex flex-col overflow-hidden';
  const head = 'px-3 py-2 bg-neutral-900/60 border-b border-neutral-800 text-[10px] font-black text-gray-500 uppercase tracking-widest';
  const th = 'text-[10px] uppercase text-gray-500 font-bold px-2 py-1 border-b border-neutral-800';

  return (
    <main className="h-screen bg-neutral-950 text-gray-100 p-3 font-mono flex flex-col overflow-hidden">
      <header className="border border-neutral-800 bg-neutral-900/40 rounded-md px-4 py-2.5 mb-3 flex items-center gap-6 shrink-0">
        <div className="flex items-center gap-2.5">
          <div className="w-7 h-7 bg-blue-600 rounded flex items-center justify-center font-bold text-base italic">C</div>
          <h1 className="text-lg font-bold text-white tracking-tighter uppercase">Chronos<span className="text-blue-500">_Compliance</span></h1>
        </div>
        <nav className="flex gap-1 text-[11px]">
          <Link href="/" className="px-3 py-1 rounded text-gray-400 hover:bg-neutral-800">Trade</Link>
          <Link href="/options" className="px-3 py-1 rounded text-gray-400 hover:bg-neutral-800">Options</Link>
          <span className="px-3 py-1 rounded bg-blue-600 text-white font-bold">Compliance</span>
        </nav>
        <div className="flex items-center gap-2 ml-4">
          <label className="text-[10px] text-gray-500 uppercase font-bold">Account</label>
          <input value={account} onChange={(e) => setAccount(e.target.value)}
            className="bg-neutral-950 border border-neutral-800 rounded px-2 py-1 text-xs text-white outline-none focus:border-blue-500 w-28" />
          <button onClick={load} className="px-3 py-1 rounded bg-neutral-800 hover:bg-neutral-700 text-[10px] font-bold uppercase">Refresh</button>
        </div>
      </header>

      <div className="grid grid-cols-12 gap-3 flex-1 min-h-0">
        {/* Surveillance */}
        <div className={`col-span-4 ${panel}`}>
          <div className={head}>Trade Surveillance</div>
          <div className="flex-1 min-h-0 overflow-y-auto custom-scrollbar p-2 text-xs">
            <div className="mb-2 text-[11px]">
              Self-trade / wash alerts: <span className={surveil && surveil.self_trade_count > 0 ? 'text-red-400 font-bold' : 'text-green-400'}>
                {surveil?.self_trade_count ?? '--'}</span>
            </div>
            {surveil?.self_trades.map((s) => (
              <div key={s.seq} className="grid grid-cols-3 py-1 border-b border-neutral-800/30">
                <span className="text-gray-400">#{s.seq}</span>
                <span className="text-red-300">{s.account}</span>
                <span className="text-right text-gray-300">{s.symbol} {px(s.price)}</span>
              </div>
            ))}
            {surveil && surveil.self_trade_count === 0 &&
              <div className="text-neutral-700 italic text-[10px] py-3">No surveillance alerts.</div>}
          </div>
        </div>

        {/* Statement */}
        <div className={`col-span-8 ${panel}`}>
          <div className={head}>Account Statement · {account}</div>
          <div className="flex-1 min-h-0 overflow-y-auto custom-scrollbar p-3 text-xs space-y-4">
            <div className="flex gap-6">
              <div><span className="text-gray-500 text-[10px] uppercase">Ending cash</span>
                <div className="text-base font-bold text-gray-100">${stmt ? cents(stmt.ending_cash_cents) : '--'}</div></div>
              <div><span className="text-gray-500 text-[10px] uppercase">Reserved</span>
                <div className="text-base font-bold text-gray-400">${stmt ? cents(stmt.reserved_cents) : '--'}</div></div>
            </div>

            <div>
              <div className="text-[10px] uppercase text-gray-500 font-bold mb-1">Cash postings</div>
              <div className="grid grid-cols-2"><span className={th}>Txn</span><span className={`${th} text-right`}>Δ</span></div>
              {stmt?.cash_postings.map((p, i) => (
                <div key={i} className="grid grid-cols-2 py-0.5 border-b border-neutral-800/20">
                  <span className="text-gray-400 truncate">{p.txn}</span>
                  <span className={`text-right ${p.delta >= 0 ? 'text-green-400' : 'text-red-400'}`}>{cents(p.delta)}</span>
                </div>
              ))}
            </div>

            <div>
              <div className="text-[10px] uppercase text-gray-500 font-bold mb-1">Trades</div>
              {stmt?.trades.map((t) => (
                <div key={t.seq} className="grid grid-cols-4 py-0.5 border-b border-neutral-800/20">
                  <span className="text-gray-400">#{t.seq}</span>
                  <span className="text-gray-200">{t.symbol}</span>
                  <span className={t.side === 'buy' ? 'text-green-400' : 'text-red-400'}>{t.side}</span>
                  <span className="text-right text-gray-300">{px(t.price)} × {qty(t.qty)}</span>
                </div>
              ))}
              {stmt && stmt.trades.length === 0 && <div className="text-neutral-700 italic text-[10px]">No trades.</div>}
            </div>

            <div>
              <div className="text-[10px] uppercase text-gray-500 font-bold mb-1">Positions</div>
              {stmt?.positions.map((p) => (
                <div key={p.symbol} className="grid grid-cols-4 py-0.5 border-b border-neutral-800/20">
                  <span className="text-gray-200">{p.symbol}</span>
                  <span className="text-right text-gray-300">{qty(p.qty)}</span>
                  <span className="text-right text-gray-400">${cents(p.cost_cents)}</span>
                  <span className={`text-right ${p.realized_cents >= 0 ? 'text-green-400' : 'text-red-400'}`}>${cents(p.realized_cents)}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </main>
  );
}
