import { create } from 'zustand';

export interface Trade {
  buy_order_id: number;
  sell_order_id: number;
  price: number;
  quantity: number;
  timestamp: number;
}

export interface Order {
  id: number;
  symbol: string;
  price: number;
  quantity: number;
  side: number; // 0: BUY, 1: SELL
  status: number;
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
  selectedSymbol: string;
  addTrade: (trade: Trade) => void;
  updateOrderBook: (order: Order) => void;
  setSelectedSymbol: (symbol: string) => void;
}

export const useTradeStore = create<TradeStore>((set) => ({
  trades: [],
  bids: [],
  asks: [],
  selectedSymbol: 'AAPL',

  setSelectedSymbol: (symbol) => 
    set({ selectedSymbol: symbol, trades: [], bids: [], asks: [] }),

  addTrade: (trade) =>
    set((state) => ({
      trades: [trade, ...state.trades].slice(0, 50), // Keep last 50
    })),

  updateOrderBook: (order) =>
    set((state) => {
      // Only update if symbol matches
      if (order.symbol !== state.selectedSymbol) return state;

      const isBuy = order.side === 0;
      const targetBook = isBuy ? [...state.bids] : [...state.asks];
      
      const existingIndex = targetBook.findIndex((l) => l.price === order.price);
      
      if (order.quantity === 0 || order.status === 2) { // FILLED
        if (existingIndex > -1) targetBook.splice(existingIndex, 1);
      } else {
        if (existingIndex > -1) {
          targetBook[existingIndex].quantity = order.quantity;
        } else {
          targetBook.push({ price: order.price, quantity: order.quantity });
        }
      }

      // Sort books
      if (isBuy) {
        targetBook.sort((a, b) => b.price - a.price);
        return { bids: targetBook.slice(0, 20) };
      } else {
        targetBook.sort((a, b) => a.price - b.price);
        return { asks: targetBook.slice(0, 20) };
      }
    }),
}));
