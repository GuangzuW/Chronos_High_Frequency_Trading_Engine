'use client';

import { useEffect } from 'react';
import { useTradeStore } from '@/store/useTradeStore';

export default function Home() {
  const { bids, asks, trades, addTrade, updateOrderBook } = useTradeStore();

  useEffect(() => {
    const socket = new WebSocket('ws://localhost:8000/ws');

    socket.onmessage = (event) => {
      const msg = JSON.parse(event.data);
      if (msg.type === 'TRADE') {
        addTrade(msg.data);
      } else if (msg.type === 'ORDER') {
        updateOrderBook(msg.data);
      }
    };

    return () => socket.close();
  }, [addTrade, updateOrderBook]);

  return (
    <main className="min-h-screen bg-neutral-950 text-gray-100 p-4 font-mono">
      <header className="border-b border-neutral-800 pb-4 mb-6 flex justify-between items-center">
        <h1 className="text-2xl font-bold text-blue-500 tracking-tighter italic">CHRONOS_TERMINAL</h1>
        <div className="flex gap-4 text-xs">
          <span className="text-green-500">● ENGINE_ONLINE</span>
          <span className="text-gray-500">v0.1.0</span>
        </div>
      </header>

      <div className="grid grid-cols-12 gap-4 h-[calc(100vh-120px)]">
        {/* Sidebar: Order Entry */}
        <div className="col-span-3 border border-neutral-800 bg-neutral-900/50 p-4 rounded shadow-lg">
          <h2 className="text-sm font-bold mb-4 text-gray-400">ORDER_ENTRY</h2>
          {/* Placeholder for form */}
          <div className="space-y-4">
            <div className="flex gap-2">
              <button className="flex-1 bg-green-600 hover:bg-green-500 py-2 rounded text-xs font-bold transition-colors">BUY</button>
              <button className="flex-1 bg-red-600 hover:bg-red-500 py-2 rounded text-xs font-bold transition-colors">SELL</button>
            </div>
          </div>
        </div>

        {/* Center: Charts & Tape */}
        <div className="col-span-6 flex flex-col gap-4">
          <div className="flex-1 border border-neutral-800 bg-neutral-900 p-4 rounded">
            <h2 className="text-sm font-bold mb-4 text-gray-400">PRICE_CHART</h2>
            <div className="h-full w-full bg-neutral-950 rounded border border-neutral-800/50 flex items-center justify-center text-neutral-700 italic">
              Initializing Chart Canvas...
            </div>
          </div>
          <div className="h-1/3 border border-neutral-800 bg-neutral-900 p-4 rounded overflow-hidden">
            <h2 className="text-sm font-bold mb-2 text-gray-400">TRADE_TAPE</h2>
            <div className="space-y-1 text-xs">
              {trades.map((t, i) => (
                <div key={i} className="flex justify-between border-b border-neutral-800/30 py-1">
                  <span className={t.buy_order_id < t.sell_order_id ? 'text-green-400' : 'text-red-400'}>
                    {t.buy_order_id < t.sell_order_id ? '↑ BUY' : '↓ SELL'}
                  </span>
                  <span>{t.price}</span>
                  <span className="text-gray-500">{t.quantity}</span>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Right: Order Book */}
        <div className="col-span-3 border border-neutral-800 bg-neutral-900 p-4 rounded overflow-hidden flex flex-col">
          <h2 className="text-sm font-bold mb-4 text-gray-400">ORDER_BOOK</h2>
          
          <div className="flex-1 flex flex-col gap-4 text-xs">
            {/* Asks */}
            <div className="flex-1 flex flex-col-reverse justify-start overflow-hidden">
              {asks.map((a, i) => (
                <div key={i} className="flex justify-between py-1 group hover:bg-neutral-800/50 px-1">
                  <span className="text-red-400">{a.price}</span>
                  <span className="text-gray-400">{a.quantity}</span>
                </div>
              ))}
            </div>
            
            <div className="border-y border-neutral-800 py-2 flex justify-center font-bold text-lg tracking-widest bg-neutral-950">
              {trades[0]?.price || '---'}
            </div>

            {/* Bids */}
            <div className="flex-1 overflow-hidden">
              {bids.map((b, i) => (
                <div key={i} className="flex justify-between py-1 group hover:bg-neutral-800/50 px-1">
                  <span className="text-green-400">{b.price}</span>
                  <span className="text-gray-400">{b.quantity}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </main>
  );
}
