'use client';

import React, { useState } from 'react';
import { useTradeStore } from '@/store/useTradeStore';
import { placeOrder, fundAccount, addEquity } from '@/lib/api';

type OType = 'limit' | 'market' | 'stop' | 'stop_limit';

const OrderEntry = ({ onPlaced }: { onPlaced?: () => void }) => {
  const { selectedSymbol, account, setAccount } = useTradeStore();
  const [price, setPrice] = useState('');
  const [stop, setStop] = useState('');
  const [quantity, setQuantity] = useState('');
  const [orderType, setOrderType] = useState<OType>('limit');
  const [tif, setTif] = useState('gtc');
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState('');

  const needsPrice = orderType === 'limit' || orderType === 'stop_limit';
  const needsStop = orderType === 'stop' || orderType === 'stop_limit';

  const submit = async (side: 'buy' | 'sell') => {
    if (!quantity || (needsPrice && !price) || (needsStop && !stop)) return;
    setBusy(true); setMsg('');
    try {
      const order = await placeOrder({
        account, symbol: selectedSymbol, side,
        quantity: parseFloat(quantity),
        order_type: orderType,
        tif: orderType === 'limit' ? tif : 'gtc',
        ...(needsPrice ? { price: parseFloat(price) } : {}),
        ...(needsStop ? { stop_price: parseFloat(stop) } : {}),
      }) as { id: number; status: string; reject_reason?: string };
      setMsg(`#${order.id} → ${order.status}${order.reject_reason ? ': ' + order.reject_reason : ''}`);
      onPlaced?.();
    } catch (e) {
      setMsg('Error: ' + (e as Error).message);
    } finally {
      setBusy(false);
    }
  };

  const fund = async () => {
    try { await fundAccount(account, 100000); setMsg('Funded ' + account + ' $100,000'); onPlaced?.(); }
    catch (e) { setMsg('Error: ' + (e as Error).message); }
  };
  const seed = async () => {
    try { await addEquity(selectedSymbol); setMsg('Added ' + selectedSymbol); onPlaced?.(); }
    catch (e) { setMsg('Error: ' + (e as Error).message); }
  };

  const inp = 'w-full bg-neutral-950 border border-neutral-800 rounded px-2 py-1.5 text-xs text-white focus:border-blue-500 outline-none transition-colors';
  const lbl = 'text-[10px] text-gray-500 font-bold uppercase';

  return (
    <div className="space-y-3">
      <div className="space-y-1">
        <label className={lbl}>Account</label>
        <input value={account} onChange={(e) => setAccount(e.target.value)} className={inp} />
      </div>

      <div className="flex bg-neutral-950 p-0.5 rounded border border-neutral-800">
        {(['limit', 'market', 'stop', 'stop_limit'] as OType[]).map((t) => (
          <button key={t} onClick={() => setOrderType(t)}
            className={`flex-1 text-[9px] py-1 rounded font-bold transition-all ${orderType === t ? 'bg-neutral-800 text-white' : 'text-gray-500 hover:text-gray-300'}`}>
            {t.replace('_', '-').toUpperCase()}
          </button>
        ))}
      </div>

      <div className="space-y-1">
        <label className={lbl}>Symbol</label>
        <div className="w-full bg-neutral-950 border border-neutral-800 rounded px-2 py-1.5 text-xs text-blue-400 font-bold">{selectedSymbol}</div>
      </div>

      {needsPrice && (
        <div className="space-y-1">
          <label className={lbl}>Limit Price</label>
          <input type="number" placeholder="0.00" value={price} onChange={(e) => setPrice(e.target.value)} className={inp} />
        </div>
      )}
      {needsStop && (
        <div className="space-y-1">
          <label className={lbl}>Stop Price</label>
          <input type="number" placeholder="0.00" value={stop} onChange={(e) => setStop(e.target.value)} className={inp} />
        </div>
      )}
      {orderType === 'limit' && (
        <div className="space-y-1">
          <label className={lbl}>Time In Force</label>
          <select value={tif} onChange={(e) => setTif(e.target.value)} className={inp}>
            <option value="gtc">GTC</option><option value="ioc">IOC</option><option value="fok">FOK</option>
          </select>
        </div>
      )}

      <div className="space-y-1">
        <label className={lbl}>Quantity</label>
        <input type="number" placeholder="0" value={quantity} onChange={(e) => setQuantity(e.target.value)} className={inp} />
      </div>
      <div className="flex gap-2">
        {[10, 50, 100, 500].map((q) => (
          <button key={q} onClick={() => setQuantity(String(q))}
            className="flex-1 bg-neutral-900 border border-neutral-800 hover:bg-neutral-800 text-[10px] py-1.5 rounded text-gray-400 font-mono">{q}</button>
        ))}
      </div>

      <div className="pt-1 flex flex-col gap-2">
        <button onClick={() => submit('buy')} disabled={busy}
          className="w-full bg-green-600 hover:bg-green-500 disabled:bg-green-900/50 text-white py-2.5 rounded text-[11px] font-black uppercase active:scale-[0.98]">
          {busy ? 'Processing...' : `Buy ${orderType.replace('_', '-')}`}
        </button>
        <button onClick={() => submit('sell')} disabled={busy}
          className="w-full bg-red-600 hover:bg-red-500 disabled:bg-red-900/50 text-white py-2.5 rounded text-[11px] font-black uppercase active:scale-[0.98]">
          {busy ? 'Processing...' : `Sell ${orderType.replace('_', '-')}`}
        </button>
      </div>

      {msg && <div className="text-[10px] text-gray-400 break-words border-t border-neutral-800 pt-2">{msg}</div>}

      <div className="flex gap-2 border-t border-neutral-800 pt-3">
        <button onClick={seed} className="flex-1 bg-neutral-900 border border-neutral-800 hover:bg-neutral-800 text-[9px] py-1.5 rounded text-gray-400 font-bold uppercase">Add Symbol</button>
        <button onClick={fund} className="flex-1 bg-neutral-900 border border-neutral-800 hover:bg-neutral-800 text-[9px] py-1.5 rounded text-gray-400 font-bold uppercase">Fund $100k</button>
      </div>
    </div>
  );
};

export default OrderEntry;
