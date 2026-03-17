'use client';

import React, { useMemo } from 'react';
import { useTradeStore } from '@/store/useTradeStore';

const OrderBook = () => {
  const { bids, asks } = useTradeStore();

  const maxQty = useMemo(() => {
    const all = [...bids, ...asks];
    return Math.max(...all.map((l) => l.quantity), 1);
  }, [bids, asks]);

  return (
    <div className="flex-1 flex flex-col gap-4 text-xs font-mono">
      {/* Asks (Sells) - Sorted High to Low for display */}
      <div className="flex-1 flex flex-col-reverse justify-start overflow-hidden border-b border-neutral-800/50 pb-2">
        {asks.map((a, i) => (
          <div key={i} className="relative flex justify-between py-1 px-2 group hover:bg-neutral-800 transition-colors">
            <div 
              className="absolute right-0 top-0 bottom-0 bg-red-500/10 transition-all duration-300"
              style={{ width: `${(a.quantity / maxQty) * 100}%` }}
            />
            <span className="text-red-400 relative z-10">{a.price.toFixed(2)}</span>
            <span className="text-gray-400 relative z-10">{a.quantity}</span>
          </div>
        ))}
      </div>

      {/* Mid Price */}
      <div className="flex justify-center items-center py-2 bg-neutral-900 border-y border-neutral-800 shadow-inner">
        <span className="text-lg font-bold tracking-widest text-blue-400">
          {bids[0] && asks[0] ? ((bids[0].price + asks[0].price) / 2).toFixed(2) : '---'}
        </span>
      </div>

      {/* Bids (Buys) - Sorted High to Low */}
      <div className="flex-1 overflow-hidden pt-2">
        {bids.map((b, i) => (
          <div key={i} className="relative flex justify-between py-1 px-2 group hover:bg-neutral-800 transition-colors">
            <div 
              className="absolute right-0 top-0 bottom-0 bg-green-500/10 transition-all duration-300"
              style={{ width: `${(b.quantity / maxQty) * 100}%` }}
            />
            <span className="text-green-400 relative z-10">{b.price.toFixed(2)}</span>
            <span className="text-gray-400 relative z-10">{b.quantity}</span>
          </div>
        ))}
      </div>
    </div>
  );
};

export default OrderBook;
