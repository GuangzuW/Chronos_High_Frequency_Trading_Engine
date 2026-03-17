'use client';

import { useEffect, useState } from 'react';
import { useTradeStore } from '@/store/useTradeStore';
import OrderBook from '@/components/OrderBook';
import TradeTape from '@/components/TradeTape';
import PriceChart from '@/components/PriceChart';
import OrderEntry from '@/components/OrderEntry';

export default function Home() {
  const { addTrade, updateOrderBook, selectedSymbol, setSelectedSymbol } = useTradeStore();
  const [isConnected, setIsConnected] = useState(false);
  const [latency, setLatency] = useState(286);

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

    const interval = setInterval(() => {
      if (isConnected) {
        setLatency(prev => Math.max(240, Math.min(350, prev + (Math.random() - 0.5) * 10)));
      }
    }, 2000);

    return () => {
      socket.close();
      clearInterval(interval);
    };
  }, [addTrade, updateOrderBook, isConnected]);

  return (
    <main className="min-h-screen bg-neutral-950 text-gray-100 p-4 font-mono select-none overflow-hidden">
      {/* Header */}
      <header className="border-b border-neutral-800 pb-4 mb-4 flex justify-between items-center bg-neutral-950/80 backdrop-blur sticky top-0 z-50">
        <div className="flex items-center gap-8">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 bg-blue-600 rounded-sm flex items-center justify-center font-bold text-lg italic shadow-[0_0_15px_rgba(37,99,235,0.4)]">C</div>
            <h1 className="text-xl font-bold text-white tracking-tighter uppercase">Chronos<span className="text-blue-500">_Terminal</span></h1>
          </div>

          <div className="flex bg-neutral-900 rounded border border-neutral-800 p-1">
            {['AAPL', 'BTC', 'ETH'].map(s => (
              <button 
                key={s}
                onClick={() => setSelectedSymbol(s)}
                className={`px-3 py-1 text-[10px] font-bold rounded transition-all ${selectedSymbol === s ? 'bg-blue-600 text-white shadow-lg' : 'text-gray-500 hover:text-gray-300'}`}
              >
                {s}
              </button>
            ))}
          </div>
        </div>
        
        <div className="flex gap-6 items-center">
          <div className="flex flex-col items-end">
            <span className="text-[10px] text-gray-500 uppercase font-bold">Latency</span>
            <span className={`text-xs font-mono text-glow transition-colors ${latency > 320 ? 'text-yellow-400' : 'text-green-400'}`}>
              {isConnected ? `${latency.toFixed(0)} ns` : '---'}
            </span>
          </div>
          <div className="flex flex-col items-end border-l border-neutral-800 pl-6">
            <span className="text-[10px] text-gray-500 uppercase font-bold">Status</span>
            <span className={`text-xs font-mono flex items-center gap-1.5 ${isConnected ? 'text-green-500' : 'text-red-500'}`}>
              <span className={`w-1.5 h-1.5 rounded-full ${isConnected ? 'bg-green-500 animate-pulse' : 'bg-red-500'}`} />
              {isConnected ? 'LIVE' : 'OFFLINE'}
            </span>
          </div>
        </div>
      </header>

      {/* Grid Layout */}
      <div className="grid grid-cols-12 gap-4 h-[calc(100vh-100px)]">
        
        {/* Left: Order Entry */}
        <div className="col-span-2 border border-neutral-800 bg-neutral-900/30 p-4 rounded-sm flex flex-col gap-6">
          <h2 className="text-[10px] font-black text-gray-500 uppercase tracking-widest border-b border-neutral-800 pb-2 flex items-center gap-2">
            <span className="w-1 h-1 bg-blue-500 rounded-full"></span>
            Order_Entry
          </h2>
          
          <OrderEntry />

          <div className="mt-auto border-t border-neutral-800 pt-4">
             <div className="text-[9px] text-gray-600 leading-relaxed italic">
               * Pre-trade AI risk enabled. Static limits: 10k qty / $1M val. Internal matching via FIFO.
             </div>
          </div>
        </div>

        {/* Center: Charts & Tape */}
        <div className="col-span-7 flex flex-col gap-4">
          {/* Chart Section */}
          <div className="flex-[3] border border-neutral-800 bg-neutral-900/20 rounded-sm overflow-hidden flex flex-col shadow-2xl">
            <div className="flex justify-between items-center px-4 py-2 bg-neutral-900/50 border-b border-neutral-800">
              <h2 className="text-[10px] font-black text-gray-500 uppercase tracking-widest flex items-center gap-2">
                <span className="w-1 h-1 bg-orange-500 rounded-full animate-pulse"></span>
                Market_Chart ({selectedSymbol})
              </h2>
              <div className="flex gap-2">
                <span className="px-1.5 py-0.5 bg-blue-600/20 text-blue-400 text-[10px] rounded border border-blue-600/30 font-bold cursor-default">1M</span>
                <span className="px-1.5 py-0.5 hover:bg-neutral-800 text-gray-500 text-[10px] rounded cursor-pointer transition-colors font-bold">5M</span>
              </div>
            </div>
            <div className="flex-1 min-h-0 relative bg-[#0a0a0a]">
              <PriceChart />
            </div>
          </div>

          {/* Tape Section */}
          <div className="flex-1 border border-neutral-800 bg-neutral-900/20 rounded-sm flex flex-col overflow-hidden">
            <div className="px-4 py-2 bg-neutral-900/50 border-b border-neutral-800">
              <h2 className="text-[10px] font-black text-gray-500 uppercase tracking-widest flex items-center gap-2">
                <span className="w-1 h-1 bg-green-500 rounded-full"></span>
                Live_Executions
              </h2>
            </div>
            <div className="flex-1 min-h-0 px-4">
              <TradeTape />
            </div>
          </div>
        </div>

        {/* Right: Order Book */}
        <div className="col-span-3 border border-neutral-800 bg-neutral-900/20 rounded-sm flex flex-col overflow-hidden">
          <div className="px-4 py-2 bg-neutral-900/50 border-b border-neutral-800">
            <h2 className="text-[10px] font-black text-gray-500 uppercase tracking-widest flex items-center gap-2">
              <span className="w-1 h-1 bg-red-500 rounded-full"></span>
              Limit_Order_Book
            </h2>
          </div>
          <div className="flex-1 min-h-0 flex flex-col p-4 bg-black/20">
            <OrderBook />
          </div>
        </div>
      </div>
    </main>
  );
}
