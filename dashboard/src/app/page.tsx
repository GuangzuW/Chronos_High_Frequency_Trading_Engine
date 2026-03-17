'use client';

import { useEffect, useState } from 'react';
import { useTradeStore } from '@/store/useTradeStore';
import OrderBook from '@/components/OrderBook';
import TradeTape from '@/components/TradeTape';
import PriceChart from '@/components/PriceChart';

export default function Home() {
  const { addTrade, updateOrderBook } = useTradeStore();
  const [isConnected, setIsConnected] = useState(false);

  useEffect(() => {
    const socket = new WebSocket('ws://localhost:8000/ws');

    socket.onopen = () => setIsConnected(true);
    socket.onclose = () => setIsConnected(false);

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
    <main className="min-h-screen bg-neutral-950 text-gray-100 p-4 font-mono select-none overflow-hidden">
      {/* Header */}
      <header className="border-b border-neutral-800 pb-4 mb-4 flex justify-between items-center bg-neutral-950/80 backdrop-blur sticky top-0 z-50">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 bg-blue-600 rounded-sm flex items-center justify-center font-bold text-lg italic shadow-[0_0_15px_rgba(37,99,235,0.4)]">C</div>
          <h1 className="text-xl font-bold text-white tracking-tighter uppercase">Chronos<span className="text-blue-500">_Terminal</span></h1>
        </div>
        <div className="flex gap-6 items-center">
          <div className="flex flex-col items-end">
            <span className="text-[10px] text-gray-500 uppercase font-bold">Latency</span>
            <span className="text-xs text-green-400 font-mono">286 ns</span>
          </div>
          <div className="flex flex-col items-end border-l border-neutral-800 pl-6">
            <span className="text-[10px] text-gray-500 uppercase font-bold">Status</span>
            <span className={`text-xs font-mono flex items-center gap-1.5 ${isConnected ? 'text-green-500' : 'text-red-500'}`}>
              <span className={`w-1.5 h-1.5 rounded-full animate-pulse ${isConnected ? 'bg-green-500' : 'bg-red-500'}`} />
              {isConnected ? 'LIVE' : 'DISCONNECTED'}
            </span>
          </div>
        </div>
      </header>

      {/* Grid Layout */}
      <div className="grid grid-cols-12 gap-4 h-[calc(100vh-100px)]">
        
        {/* Left: Order Entry */}
        <div className="col-span-2 border border-neutral-800 bg-neutral-900/30 p-4 rounded-sm flex flex-col gap-6">
          <h2 className="text-[10px] font-black text-gray-500 uppercase tracking-widest border-b border-neutral-800 pb-2">Order_Entry</h2>
          
          <div className="space-y-4">
            <div className="space-y-1">
              <label className="text-[10px] text-gray-500 font-bold uppercase">Symbol</label>
              <input type="text" value="AAPL" readOnly className="w-full bg-neutral-950 border border-neutral-800 rounded px-2 py-1.5 text-xs focus:border-blue-500 outline-none transition-colors" />
            </div>
            
            <div className="space-y-1">
              <label className="text-[10px] text-gray-500 font-bold uppercase">Price</label>
              <input type="number" placeholder="0.00" className="w-full bg-neutral-950 border border-neutral-800 rounded px-2 py-1.5 text-xs focus:border-blue-500 outline-none" />
            </div>

            <div className="space-y-1">
              <label className="text-[10px] text-gray-500 font-bold uppercase">Quantity</label>
              <input type="number" placeholder="0" className="w-full bg-neutral-950 border border-neutral-800 rounded px-2 py-1.5 text-xs focus:border-blue-500 outline-none" />
            </div>

            <div className="pt-4 flex flex-col gap-2">
              <button className="w-full bg-green-600 hover:bg-green-500 text-white py-2.5 rounded text-[11px] font-black uppercase transition-all active:scale-[0.98] shadow-lg shadow-green-900/20">Buy Market</button>
              <button className="w-full bg-red-600 hover:bg-red-500 text-white py-2.5 rounded text-[11px] font-black uppercase transition-all active:scale-[0.98] shadow-lg shadow-red-900/20">Sell Market</button>
            </div>
          </div>

          <div className="mt-auto border-t border-neutral-800 pt-4">
             <div className="text-[9px] text-gray-600 leading-relaxed italic">
               * Pre-trade risk AI enabled. Static limits: 10k qty / $1M val.
             </div>
          </div>
        </div>

        {/* Center: Charts & Tape */}
        <div className="col-span-7 flex flex-col gap-4">
          {/* Chart Section */}
          <div className="flex-[3] border border-neutral-800 bg-neutral-900/20 rounded-sm overflow-hidden flex flex-col">
            <div className="flex justify-between items-center px-4 py-2 bg-neutral-900/50 border-b border-neutral-800">
              <h2 className="text-[10px] font-black text-gray-500 uppercase tracking-widest">Market_Chart</h2>
              <div className="flex gap-2">
                <span className="px-1.5 py-0.5 bg-blue-600/20 text-blue-400 text-[10px] rounded border border-blue-600/30">1M</span>
                <span className="px-1.5 py-0.5 hover:bg-neutral-800 text-gray-500 text-[10px] rounded cursor-pointer transition-colors">5M</span>
              </div>
            </div>
            <div className="flex-1 min-h-0 relative">
              <PriceChart />
            </div>
          </div>

          {/* Tape Section */}
          <div className="flex-1 border border-neutral-800 bg-neutral-900/20 rounded-sm flex flex-col overflow-hidden">
            <div className="px-4 py-2 bg-neutral-900/50 border-b border-neutral-800">
              <h2 className="text-[10px] font-black text-gray-500 uppercase tracking-widest">Live_Executions</h2>
            </div>
            <div className="flex-1 min-h-0 px-4">
              <TradeTape />
            </div>
          </div>
        </div>

        {/* Right: Order Book */}
        <div className="col-span-3 border border-neutral-800 bg-neutral-900/20 rounded-sm flex flex-col overflow-hidden">
          <div className="px-4 py-2 bg-neutral-900/50 border-b border-neutral-800">
            <h2 className="text-[10px] font-black text-gray-500 uppercase tracking-widest">Limit_Order_Book</h2>
          </div>
          <div className="flex-1 min-h-0 flex flex-col p-4">
            <OrderBook />
          </div>
        </div>
      </div>
    </main>
  );
}
