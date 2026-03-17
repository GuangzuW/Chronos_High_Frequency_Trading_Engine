'use client';

import React, { useState } from 'react';
import { useTradeStore } from '@/store/useTradeStore';

const OrderEntry = () => {
  const { selectedSymbol } = useTradeStore();
  const [price, setPrice] = useState<string>('');
  const [quantity, setQuantity] = useState<string>('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [orderType, setOrderType] = useState<'LIMIT' | 'MARKET'>('LIMIT');

  const placeOrder = async (side: number) => {
    if ((orderType === 'LIMIT' && !price) || !quantity) return;
    
    setIsSubmitting(true);
    try {
      const response = await fetch('http://localhost:8000/order', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          symbol: selectedSymbol,
          price: orderType === 'LIMIT' ? parseFloat(price) : (side === 0 ? 999999 : 1), // Aggressive price for market simulation
          quantity: parseInt(quantity),
          side: side
        }),
      });
      
      if (response.ok) {
        console.log('Order submitted successfully');
      }
    } catch (error) {
      console.error('Failed to submit order:', error);
      alert('Failed to connect to API Bridge. Ensure it is running on port 8000.');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="space-y-4">
      {/* Type Toggle */}
      <div className="flex bg-neutral-950 p-0.5 rounded border border-neutral-800">
        <button 
          onClick={() => setOrderType('LIMIT')}
          className={`flex-1 text-[9px] py-1 rounded font-bold transition-all ${orderType === 'LIMIT' ? 'bg-neutral-800 text-white shadow-sm' : 'text-gray-500 hover:text-gray-300'}`}
        >
          LIMIT
        </button>
        <button 
          onClick={() => setOrderType('MARKET')}
          className={`flex-1 text-[9px] py-1 rounded font-bold transition-all ${orderType === 'MARKET' ? 'bg-neutral-800 text-white shadow-sm' : 'text-gray-500 hover:text-gray-300'}`}
        >
          MARKET
        </button>
      </div>

      <div className="space-y-1">
        <label className="text-[10px] text-gray-500 font-bold uppercase">Symbol</label>
        <div className="w-full bg-neutral-950 border border-neutral-800 rounded px-2 py-1.5 text-xs text-blue-400 font-bold">
          {selectedSymbol}
        </div>
      </div>
      
      {orderType === 'LIMIT' && (
        <div className="space-y-1 animate-in fade-in duration-200">
          <label className="text-[10px] text-gray-500 font-bold uppercase">Price</label>
          <input 
            type="number" 
            placeholder="0.00" 
            value={price}
            onChange={(e) => setPrice(e.target.value)}
            className="w-full bg-neutral-950 border border-neutral-800 rounded px-2 py-1.5 text-xs text-white focus:border-blue-500 outline-none transition-colors" 
          />
        </div>
      )}

      <div className="space-y-1">
        <label className="text-[10px] text-gray-500 font-bold uppercase">Quantity</label>
        <input 
          type="number" 
          placeholder="0" 
          value={quantity}
          onChange={(e) => setQuantity(e.target.value)}
          className="w-full bg-neutral-950 border border-neutral-800 rounded px-2 py-1.5 text-xs text-white focus:border-blue-500 outline-none transition-colors" 
        />
      </div>

      <div className="flex gap-2 mb-2">
        {[10, 50, 100, 500].map((qty) => (
          <button 
            key={qty}
            onClick={() => setQuantity(qty.toString())}
            className="flex-1 bg-neutral-900 border border-neutral-800 hover:bg-neutral-800 text-[10px] py-1.5 rounded transition-colors text-gray-400 font-mono"
          >
            {qty}
          </button>
        ))}
      </div>

      <div className="pt-2 flex flex-col gap-2">
        <button 
          onClick={() => placeOrder(0)}
          disabled={isSubmitting}
          className="w-full bg-green-600 hover:bg-green-500 disabled:bg-green-900/50 text-white py-2.5 rounded text-[11px] font-black uppercase transition-all active:scale-[0.98] shadow-lg shadow-green-900/20"
        >
          {isSubmitting ? 'Processing...' : `Buy ${orderType.toLowerCase()}`}
        </button>
        <button 
          onClick={() => placeOrder(1)}
          disabled={isSubmitting}
          className="w-full bg-red-600 hover:bg-red-500 disabled:bg-red-900/50 text-white py-2.5 rounded text-[11px] font-black uppercase transition-all active:scale-[0.98] shadow-lg shadow-red-900/20"
        >
          {isSubmitting ? 'Processing...' : `Sell ${orderType.toLowerCase()}`}
        </button>
      </div>
    </div>
  );
};

export default OrderEntry;
