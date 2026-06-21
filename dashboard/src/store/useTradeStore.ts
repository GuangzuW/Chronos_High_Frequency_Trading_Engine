import { create } from 'zustand';
import type { Snapshot, Balance, Position, OrderInfo } from '@/lib/api';

export interface Trade {
  buy_order_id: number;
  sell_order_id: number;
  price: number;
  quantity: number;
  timestamp: number;
}

interface OrderBookLevel {
  price: number;
  quantity: number;
}

interface TradeStore {
  trades: Trade[];
  bids: OrderBookLevel[];
  asks: OrderBookLevel[];
  last: number | null;
  bestBid: number | null;
  bestAsk: number | null;
  selectedSymbol: string;
  account: string;
  symbols: string[];
  balance: Balance | null;
  positions: Position[];
  orders: OrderInfo[];
  toasts: Toast[];
  defaultQty: number;
  setSelectedSymbol: (symbol: string) => void;
  setAccount: (account: string) => void;
  setSymbols: (symbols: string[]) => void;
  setDefaultQty: (n: number) => void;
  applySnapshot: (snap: Snapshot) => void;
  applyAccount: (balance: Balance, positions: Position[], orders: OrderInfo[]) => void;
  pushToast: (text: string, kind?: string) => void;
  dismissToast: (id: number) => void;
}

export interface Toast { id: number; text: string; kind: string }
let toastSeq = 0;

export const useTradeStore = create<TradeStore>((set) => ({
  trades: [],
  bids: [],
  asks: [],
  last: null,
  bestBid: null,
  bestAsk: null,
  selectedSymbol: 'AAPL',
  account: 'trader1',
  symbols: ['AAPL', 'BTC', 'ETH'],
  balance: null,
  positions: [],
  orders: [],
  toasts: [],
  defaultQty: 10,

  setSelectedSymbol: (symbol) =>
    set({ selectedSymbol: symbol, trades: [], bids: [], asks: [], last: null, bestBid: null, bestAsk: null }),
  setAccount: (account) => set({ account, balance: null, positions: [], orders: [] }),
  setSymbols: (symbols) => set({ symbols }),
  setDefaultQty: (n) => set({ defaultQty: n }),

  applySnapshot: (snap) =>
    set({
      bids: snap.bids,
      asks: snap.asks,
      last: snap.last,
      bestBid: snap.best_bid,
      bestAsk: snap.best_ask,
      trades: [...snap.trades].reverse().map((t) => ({
        buy_order_id: t.buy_order_id,
        sell_order_id: t.sell_order_id,
        price: t.price,
        quantity: t.quantity,
        timestamp: t.ts_ns,
      })),
    }),

  applyAccount: (balance, positions, orders) => set({ balance, positions, orders }),

  pushToast: (text, kind = 'info') =>
    set((s) => ({ toasts: [...s.toasts, { id: ++toastSeq, text, kind }].slice(-6) })),
  dismissToast: (id) => set((s) => ({ toasts: s.toasts.filter((t) => t.id !== id) })),
}));
