'use client';

import { useCallback, useEffect, useState, type ReactNode } from 'react';
import Link from 'next/link';
import { useTradeStore } from '@/store/useTradeStore';
import { getSnapshot, getInstruments, getBalance, getPositions, getOrders, subscribeStream, placeOrder } from '@/lib/api';
import OrderBook from '@/components/OrderBook';
import TradeTape from '@/components/TradeTape';
import PriceChart from '@/components/PriceChart';
import OrderEntry from '@/components/OrderEntry';
import AccountSummary from '@/components/AccountSummary';
import Positions from '@/components/Positions';
import OpenOrders from '@/components/OpenOrders';
import DepthChart from '@/components/DepthChart';
import GreeksPanel from '@/components/GreeksPanel';
import CashCurve from '@/components/CashCurve';
import Toaster from '@/components/Toaster';
import Watchlist from '@/components/Watchlist';
import PriceLadder from '@/components/PriceLadder';

function TabPanel({ tabs, className = '' }:
  { tabs: { label: string; dot: string; node: ReactNode }[]; className?: string }) {
  const [active, setActive] = useState(0);
  return (
    <div className={`border border-neutral-800 bg-neutral-900/20 rounded-md flex flex-col overflow-hidden ${className}`}>
      <div className="flex bg-neutral-900/60 border-b border-neutral-800 shrink-0">
        {tabs.map((t, i) => (
          <button key={t.label} onClick={() => setActive(i)}
            className={`px-3 py-2 text-[10px] font-black uppercase tracking-widest flex items-center gap-2 transition-colors ${active === i ? 'text-gray-200 border-b-2 border-blue-500' : 'text-gray-600 hover:text-gray-400'}`}>
            <span className={`w-1 h-1 rounded-full ${t.dot}`} />{t.label}
          </button>
        ))}
      </div>
      <div className="flex-1 min-h-0">{tabs[active].node}</div>
    </div>
  );
}

function Panel({ title, dot, children, className = '' }:
  { title: string; dot: string; children: ReactNode; className?: string }) {
  return (
    <div className={`border border-neutral-800 bg-neutral-900/20 rounded-md flex flex-col overflow-hidden ${className}`}>
      <div className="px-3 py-2 bg-neutral-900/60 border-b border-neutral-800 shrink-0">
        <h2 className="text-[10px] font-black text-gray-500 uppercase tracking-widest flex items-center gap-2">
          <span className={`w-1 h-1 rounded-full ${dot}`} />{title}
        </h2>
      </div>
      <div className="flex-1 min-h-0">{children}</div>
    </div>
  );
}

export default function Home() {
  const {
    selectedSymbol, setSelectedSymbol, applySnapshot, applyAccount,
    symbols, setSymbols, account, setAccount, last, bestBid, bestAsk, pushToast,
    defaultQty, setDefaultQty,
  } = useTradeStore();
  const [isConnected, setIsConnected] = useState(false);
  const [showHelp, setShowHelp] = useState(false);

  // Load persisted UI prefs once (client-only; SSR-safe).
  useEffect(() => {
    try {
      const raw = localStorage.getItem('chronos-prefs');
      if (raw) {
        const p = JSON.parse(raw);
        if (p.account) setAccount(p.account);
        if (p.selectedSymbol) setSelectedSymbol(p.selectedSymbol);
        if (typeof p.defaultQty === 'number') setDefaultQty(p.defaultQty);
      }
    } catch { /* ignore */ }
  }, [setAccount, setSelectedSymbol, setDefaultQty]);

  // Persist prefs on change.
  useEffect(() => {
    try { localStorage.setItem('chronos-prefs', JSON.stringify({ account, selectedSymbol, defaultQty })); }
    catch { /* ignore */ }
  }, [account, selectedSymbol, defaultQty]);

  useEffect(() => {
    getInstruments()
      .then((r) => { if (r.instruments.length) setSymbols(r.instruments.map((i) => i.symbol)); })
      .catch(() => {});
  }, [setSymbols]);

  const refreshMarket = useCallback(async () => {
    try { applySnapshot(await getSnapshot(selectedSymbol)); setIsConnected(true); }
    catch { setIsConnected(false); }
  }, [selectedSymbol, applySnapshot]);

  const refreshAccount = useCallback(async () => {
    try {
      const [b, p, o] = await Promise.all([
        getBalance(account), getPositions(account), getOrders(account),
      ]);
      applyAccount(b, p.positions, o.orders);
    } catch { /* account may not be funded yet */ }
  }, [account, applyAccount]);

  const refreshAll = useCallback(() => { refreshMarket(); refreshAccount(); }, [refreshMarket, refreshAccount]);

  useEffect(() => {
    let alive = true;
    const tick = () => { if (alive) refreshAll(); };
    tick();
    const es = subscribeStream((ev) => {
      if (ev.type === 'order' && ev.account === account && ev.id) {
        pushToast(`#${ev.id} ${ev.symbol} ${ev.side} → ${ev.status}`, ev.status);
      }
      if (!ev.symbol || ev.symbol === selectedSymbol) tick();
    });
    es.onopen = () => setIsConnected(true);
    es.onerror = () => setIsConnected(false);
    const poll = setInterval(tick, 1500);
    return () => { alive = false; es.close(); clearInterval(poll); };
  }, [refreshAll, selectedSymbol, account, pushToast]);

  // Fast order entry: marketable limit at the touch (buy lifts ask, sell hits bid).
  const quickOrder = useCallback(async (side: 'buy' | 'sell') => {
    const px = side === 'buy' ? (bestAsk ?? last) : (bestBid ?? last);
    if (px == null) { pushToast('No price available to trade', 'rejected'); return; }
    try {
      await placeOrder({ account, symbol: selectedSymbol, side, price: px, quantity: defaultQty, order_type: 'limit', tif: 'gtc' });
      refreshAll();
    } catch (e) { pushToast('Error: ' + (e as Error).message, 'rejected'); }
  }, [account, selectedSymbol, bestAsk, bestBid, last, defaultQty, pushToast, refreshAll]);

  // Keyboard shortcuts (ignored while typing in a field).
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      const tag = (e.target as HTMLElement)?.tagName;
      if (tag === 'INPUT' || tag === 'SELECT' || tag === 'TEXTAREA') return;
      if (e.key === 'b' || e.key === 'B') quickOrder('buy');
      else if (e.key === 's' || e.key === 'S') quickOrder('sell');
      else if (e.key === '?') setShowHelp((h) => !h);
      else if (e.key === 'Escape') setShowHelp(false);
      else if ((e.key === 'ArrowDown' || e.key === 'ArrowUp') && symbols.length) {
        const i = symbols.indexOf(selectedSymbol);
        const n = e.key === 'ArrowDown'
          ? (i + 1) % symbols.length
          : (i - 1 + symbols.length) % symbols.length;
        setSelectedSymbol(symbols[n]);
        e.preventDefault();
      }
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [quickOrder, symbols, selectedSymbol, setSelectedSymbol]);

  const spread = bestBid != null && bestAsk != null ? bestAsk - bestBid : null;

  return (
    <main className="h-screen bg-neutral-950 text-gray-100 p-3 font-mono select-none overflow-hidden flex flex-col">
      <header className="border border-neutral-800 bg-neutral-900/40 rounded-md px-4 py-2.5 mb-3 flex justify-between items-center shrink-0">
        <div className="flex items-center gap-6">
          <div className="flex items-center gap-2.5">
            <div className="w-7 h-7 bg-blue-600 rounded flex items-center justify-center font-bold text-base italic shadow-[0_0_15px_rgba(37,99,235,0.4)]">C</div>
            <h1 className="text-lg font-bold text-white tracking-tighter uppercase">Chronos<span className="text-blue-500">_Trade</span></h1>
          </div>
          <nav className="flex gap-1 text-[11px]">
            <span className="px-3 py-1 rounded bg-blue-600 text-white font-bold">Trade</span>
            <Link href="/options" className="px-3 py-1 rounded text-gray-400 hover:bg-neutral-800">Options</Link>
            <Link href="/compliance" className="px-3 py-1 rounded text-gray-400 hover:bg-neutral-800">Compliance</Link>
          </nav>
          <div className="flex bg-neutral-900 rounded border border-neutral-800 p-1">
            {symbols.map((s) => (
              <button key={s} onClick={() => setSelectedSymbol(s)}
                className={`px-3 py-1 text-[10px] font-bold rounded transition-all ${selectedSymbol === s ? 'bg-blue-600 text-white shadow-lg' : 'text-gray-500 hover:text-gray-300'}`}>
                {s}
              </button>
            ))}
          </div>
          <div className="flex items-baseline gap-3">
            <span className="text-2xl font-bold text-white tabular-nums">{last != null ? last.toFixed(2) : '--'}</span>
            <span className="text-[11px] text-gray-500 tabular-nums">
              {bestBid != null ? `bid ${bestBid.toFixed(2)}` : ''} {bestAsk != null ? `ask ${bestAsk.toFixed(2)}` : ''}
              {spread != null ? `  spr ${spread.toFixed(2)}` : ''}
            </span>
          </div>
        </div>
        <div className="flex items-center gap-4">
          <button onClick={() => setShowHelp(true)} title="Keyboard shortcuts (?)"
            className="w-6 h-6 rounded border border-neutral-700 text-gray-400 hover:border-blue-500 hover:text-blue-400 text-xs font-bold">?</button>
          <div className="flex flex-col items-end">
            <span className="text-[10px] text-gray-500 uppercase font-bold">{account}</span>
            <span className={`text-xs font-mono flex items-center gap-1.5 ${isConnected ? 'text-green-500' : 'text-red-500'}`}>
              <span className={`w-1.5 h-1.5 rounded-full ${isConnected ? 'bg-green-500 animate-pulse' : 'bg-red-500'}`} />
              {isConnected ? 'LIVE' : 'OFFLINE'}
            </span>
          </div>
        </div>
      </header>

      <div className="grid grid-cols-12 gap-3 flex-1 min-h-0">
        {/* Left: ticket + account + watchlist */}
        <div className="col-span-3 flex flex-col gap-3 min-h-0">
          <Panel title="Order Ticket" dot="bg-blue-500" className="shrink-0">
            <div className="p-3 overflow-y-auto custom-scrollbar"><OrderEntry onPlaced={refreshAll} /></div>
          </Panel>
          <Panel title="Account" dot="bg-emerald-500" className="shrink-0">
            <div className="p-3"><AccountSummary /></div>
          </Panel>
          <Panel title="Watchlist" dot="bg-sky-500" className="flex-1">
            <Watchlist />
          </Panel>
        </div>

        {/* Center: chart + (orders | tape) */}
        <div className="col-span-6 flex flex-col gap-3 min-h-0">
          <Panel title={`Chart · ${selectedSymbol}`} dot="bg-orange-500 animate-pulse" className="flex-[3]">
            <div className="w-full h-full bg-neutral-950"><PriceChart /></div>
          </Panel>
          <TabPanel className="flex-[2]" tabs={[
            { label: 'Open Orders', dot: 'bg-yellow-500', node: <OpenOrders onChanged={refreshAll} /> },
            { label: 'Time & Sales', dot: 'bg-green-500', node: <div className="px-3 h-full"><TradeTape /></div> },
            { label: 'Depth', dot: 'bg-cyan-500', node: <DepthChart /> },
          ]} />
        </div>

        {/* Right: book/ladder + positions/greeks/cash */}
        <div className="col-span-3 flex flex-col gap-3 min-h-0">
          <TabPanel className="flex-[3]" tabs={[
            { label: 'Book', dot: 'bg-red-500', node: <div className="h-full flex flex-col p-3 bg-black/20"><OrderBook /></div> },
            { label: 'Ladder', dot: 'bg-amber-500', node: <PriceLadder onPlaced={refreshAll} /> },
          ]} />
          <TabPanel className="flex-[2]" tabs={[
            { label: 'Positions', dot: 'bg-purple-500', node: <Positions /> },
            { label: 'Greeks', dot: 'bg-pink-500', node: <GreeksPanel /> },
            { label: 'Cash', dot: 'bg-emerald-500', node: <CashCurve /> },
          ]} />
        </div>
      </div>
      <Toaster />

      {showHelp && (
        <div className="fixed inset-0 z-50 bg-black/60 flex items-center justify-center" onClick={() => setShowHelp(false)}>
          <div className="bg-neutral-900 border border-neutral-700 rounded-lg p-6 w-80 text-xs font-mono"
            onClick={(e) => e.stopPropagation()}>
            <h3 className="text-sm font-bold text-white uppercase tracking-widest mb-4 flex items-center gap-2">
              <span className="w-1.5 h-1.5 bg-blue-500 rounded-full" /> Keyboard Shortcuts
            </h3>
            {[
              ['B', 'Buy at the offer (marketable limit)'],
              ['S', 'Sell at the bid'],
              ['↑ / ↓', 'Previous / next symbol'],
              ['?', 'Toggle this help'],
              ['Esc', 'Close'],
            ].map(([k, d]) => (
              <div key={k} className="flex justify-between py-1 border-b border-neutral-800/50">
                <kbd className="px-1.5 py-0.5 bg-neutral-950 border border-neutral-700 rounded text-blue-300">{k}</kbd>
                <span className="text-gray-400 text-right ml-3">{d}</span>
              </div>
            ))}
            <div className="mt-4 flex items-center justify-between">
              <label className="text-[10px] uppercase text-gray-500 font-bold">Hotkey qty</label>
              <input type="number" value={defaultQty}
                onChange={(e) => setDefaultQty(parseFloat(e.target.value) || 0)}
                className="w-24 bg-neutral-950 border border-neutral-800 rounded px-2 py-1 text-white outline-none focus:border-blue-500" />
            </div>
            <div className="mt-2 text-[10px] text-gray-600">Shortcuts use the selected symbol &amp; account. Ignored while typing in a field. Prefs persist locally.</div>
          </div>
        </div>
      )}
    </main>
  );
}
