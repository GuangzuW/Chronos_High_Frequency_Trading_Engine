'use client';

import React, { useState } from 'react';
import { useTradeStore } from '@/store/useTradeStore';
import { cancelOrder } from '@/lib/api';

const OPEN = new Set(['new', 'partial', 'pending']);
const fmt = (n: number, d = 2) =>
  n.toLocaleString(undefined, { minimumFractionDigits: d, maximumFractionDigits: d });

const statusColor: Record<string, string> = {
  new: 'text-blue-400', partial: 'text-yellow-400', pending: 'text-purple-400',
  filled: 'text-green-400', canceled: 'text-gray-500', rejected: 'text-red-400',
};

const OpenOrders = ({ onChanged }: { onChanged?: () => void }) => {
  const { orders } = useTradeStore();
  const [busy, setBusy] = useState<number | null>(null);
  const rows = orders.slice(0, 40);

  const cancel = async (id: number) => {
    setBusy(id);
    try { await cancelOrder(id); onChanged?.(); }
    catch { /* already terminal */ }
    finally { setBusy(null); }
  };

  return (
    <div className="h-full overflow-y-auto custom-scrollbar text-xs font-mono">
      <div className="grid grid-cols-[40px_50px_60px_1fr_60px_60px_50px] text-[10px] uppercase text-gray-500 font-bold sticky top-0 bg-neutral-900 py-1.5 px-2 border-b border-neutral-800 gap-1">
        <span>ID</span><span>Side</span><span>Type</span><span className="text-right">Price</span>
        <span className="text-right">Filled</span><span className="text-right">Status</span><span></span>
      </div>
      {rows.length === 0 && (
        <div className="text-center text-neutral-700 py-6 italic uppercase tracking-widest text-[10px]">No orders</div>
      )}
      {rows.map((o) => (
        <div key={o.id} className="grid grid-cols-[40px_50px_60px_1fr_60px_60px_50px] gap-1 py-1.5 px-2 border-b border-neutral-800/30 hover:bg-neutral-800/40 items-center">
          <span className="text-gray-500">{o.id}</span>
          <span className={o.side === 'buy' ? 'text-green-400 font-bold' : 'text-red-400 font-bold'}>{o.side.toUpperCase()}</span>
          <span className="text-gray-400">{o.order_type.replace('_', '-')}</span>
          <span className="text-right text-gray-200">{o.order_type === 'market' ? 'MKT' : fmt(o.price)}</span>
          <span className="text-right text-gray-400">{fmt(o.filled, 0)}/{fmt(o.quantity, 0)}</span>
          <span className={`text-right ${statusColor[o.status] || 'text-gray-300'}`}>{o.status}</span>
          <span className="text-right">
            {OPEN.has(o.status) && (
              <button onClick={() => cancel(o.id)} disabled={busy === o.id}
                className="text-[9px] px-1.5 py-0.5 rounded border border-neutral-700 text-gray-400 hover:border-red-500 hover:text-red-400 transition-colors">
                {busy === o.id ? '...' : '✕'}
              </button>
            )}
          </span>
        </div>
      ))}
    </div>
  );
};

export default OpenOrders;
