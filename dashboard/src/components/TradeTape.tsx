'use client';

import React from 'react';
import { useTradeStore } from '@/store/useTradeStore';

const TradeTape = () => {
  const { trades } = useTradeStore();

  return (
    <div className="h-full overflow-y-auto custom-scrollbar pr-2">
      <div className="grid grid-cols-3 text-[10px] uppercase text-gray-500 font-bold mb-2 sticky top-0 bg-neutral-900 py-1 border-b border-neutral-800">
        <span>Side</span>
        <span className="text-right">Price</span>
        <span className="text-right">Qty</span>
      </div>
      <div className="space-y-1">
        {trades.map((t, i) => (
          <div 
            key={i} 
            className="grid grid-cols-3 text-[11px] py-1 border-b border-neutral-800/20 animate-in fade-in slide-in-from-top-1 duration-300"
          >
            <span className={t.buy_order_id < t.sell_order_id ? 'text-green-400 font-bold' : 'text-red-400 font-bold'}>
              {t.buy_order_id < t.sell_order_id ? 'BUY' : 'SELL'}
            </span>
            <span className="text-right text-gray-200">{t.price.toFixed(2)}</span>
            <span className="text-right text-gray-400">{t.quantity}</span>
          </div>
        ))}
        {trades.length === 0 && (
          <div className="text-center text-neutral-700 py-8 italic text-xs uppercase tracking-widest">
            Waiting for matches...
          </div>
        )}
      </div>
    </div>
  );
};

export default TradeTape;
