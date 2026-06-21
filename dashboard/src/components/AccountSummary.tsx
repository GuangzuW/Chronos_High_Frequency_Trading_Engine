'use client';

import React from 'react';
import { useTradeStore } from '@/store/useTradeStore';

const money = (n: number | undefined) =>
  n == null ? '--' : n.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 });

const AccountSummary = () => {
  const { balance, positions } = useTradeStore();
  const realized = positions.reduce((a, p) => a + p.realized_pnl, 0);

  return (
    <div className="grid grid-cols-2 gap-2 text-xs font-mono">
      <Stat label="Cash" value={`$${money(balance?.cash)}`} />
      <Stat label="Buying Power" value={`$${money(balance?.available)}`} accent />
      <Stat label="Reserved" value={`$${money(balance?.reserved)}`} muted />
      <Stat label="Realized P&L" value={`$${money(realized)}`} pnl={realized} />
    </div>
  );
};

const Stat = ({ label, value, accent, muted, pnl }:
  { label: string; value: string; accent?: boolean; muted?: boolean; pnl?: number }) => {
  const color = pnl != null ? (pnl > 0 ? 'text-green-400' : pnl < 0 ? 'text-red-400' : 'text-gray-200')
    : accent ? 'text-blue-400' : muted ? 'text-gray-500' : 'text-gray-100';
  return (
    <div className="bg-neutral-950 border border-neutral-800 rounded px-3 py-2">
      <div className="text-[9px] uppercase text-gray-500 font-bold tracking-wider">{label}</div>
      <div className={`text-sm font-bold mt-0.5 ${color}`}>{value}</div>
    </div>
  );
};

export default AccountSummary;
