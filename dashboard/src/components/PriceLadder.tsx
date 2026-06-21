'use client';

import React, { useMemo, useState } from 'react';
import { useTradeStore } from '@/store/useTradeStore';
import { placeOrder } from '@/lib/api';

// Click-to-trade DOM ladder: left = bid sizes (click to SELL into), right = ask sizes
// (click to BUY from). Order quantity comes from the input at the top.
const PriceLadder = ({ onPlaced }: { onPlaced?: () => void }) => {
  const { bids, asks, selectedSymbol, account, last, pushToast } = useTradeStore();
  const [qty, setQty] = useState('10');
  const [busy, setBusy] = useState(false);

  const { prices, bidMap, askMap, maxSize } = useMemo(() => {
    const bidMap = new Map(bids.map((b) => [b.price, b.quantity]));
    const askMap = new Map(asks.map((a) => [a.price, a.quantity]));
    const prices = [...new Set([...bidMap.keys(), ...askMap.keys()])].sort((a, b) => b - a);
    const maxSize = Math.max(1, ...bids.map((b) => b.quantity), ...asks.map((a) => a.quantity));
    return { prices, bidMap, askMap, maxSize };
  }, [bids, asks]);

  const trade = async (price: number, side: 'buy' | 'sell') => {
    const q = Number(qty);
    if (!q) return;
    setBusy(true);
    try {
      await placeOrder({ account, symbol: selectedSymbol, side, price, quantity: q, order_type: 'limit', tif: 'gtc' });
      onPlaced?.();
    } catch (e) {
      pushToast('Error: ' + (e as Error).message, 'rejected');
    } finally {
      setBusy(false);
    }
  };

  const bar = (size: number, side: 'bid' | 'ask') => (
    <span className={`absolute top-0 bottom-0 ${side === 'bid' ? 'right-0 bg-green-500/15' : 'left-0 bg-red-500/15'}`}
      style={{ width: `${(size / maxSize) * 100}%` }} />
  );

  return (
    <div className="h-full flex flex-col text-xs font-mono">
      <div className="flex items-center gap-2 px-3 py-2 border-b border-neutral-800 shrink-0">
        <label className="text-[10px] text-gray-500 uppercase font-bold">Qty</label>
        <input type="number" value={qty} onChange={(e) => setQty(e.target.value)}
          className="w-20 bg-neutral-950 border border-neutral-800 rounded px-2 py-1 text-white outline-none focus:border-blue-500" />
        <span className="text-[10px] text-gray-600">click bid → sell · ask → buy</span>
      </div>
      <div className="flex-1 min-h-0 overflow-y-auto custom-scrollbar">
        <div className="grid grid-cols-3 text-[10px] uppercase text-gray-500 font-bold px-2 py-1 sticky top-0 bg-neutral-900 border-b border-neutral-800">
          <span>Bid</span><span className="text-center">Price</span><span className="text-right">Ask</span>
        </div>
        {prices.length === 0 && (
          <div className="text-center text-neutral-700 italic uppercase tracking-widest text-[10px] py-6">Empty book</div>
        )}
        {prices.map((p) => {
          const bidSz = bidMap.get(p);
          const askSz = askMap.get(p);
          return (
            <div key={p} className="grid grid-cols-3 items-stretch border-b border-neutral-800/20 h-7">
              <button disabled={busy || bidSz == null} onClick={() => trade(p, 'sell')}
                className={`relative text-left px-2 ${bidSz != null ? 'text-green-400 hover:bg-green-500/20 cursor-pointer' : 'text-neutral-700 cursor-default'}`}>
                {bidSz != null && bar(bidSz, 'bid')}
                <span className="relative z-10">{bidSz != null ? bidSz.toFixed(0) : ''}</span>
              </button>
              <span className={`text-center self-center font-bold ${last != null && p === last ? 'text-blue-400' : 'text-gray-200'}`}>
                {p.toFixed(2)}
              </span>
              <button disabled={busy || askSz == null} onClick={() => trade(p, 'buy')}
                className={`relative text-right px-2 ${askSz != null ? 'text-red-400 hover:bg-red-500/20 cursor-pointer' : 'text-neutral-700 cursor-default'}`}>
                {askSz != null && bar(askSz, 'ask')}
                <span className="relative z-10">{askSz != null ? askSz.toFixed(0) : ''}</span>
              </button>
            </div>
          );
        })}
      </div>
    </div>
  );
};

export default PriceLadder;
