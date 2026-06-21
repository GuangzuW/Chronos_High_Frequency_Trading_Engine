// Client for the Chronos `services/api` backend (the runnable Python reference).
// Override the base with NEXT_PUBLIC_API_BASE (defaults to the local dev server).

export const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE || 'http://localhost:8080';

export interface BookLevel { price: number; quantity: number }
export interface TapeTrade {
  seq: number; price: number; quantity: number;
  buy_order_id: number; sell_order_id: number; ts_ns: number;
}
export interface Snapshot {
  symbol: string;
  last: number | null;
  best_bid: number | null;
  best_ask: number | null;
  bids: BookLevel[];
  asks: BookLevel[];
  trades: TapeTrade[];
}
export interface Balance { account: string; cash: number; available: number; reserved: number }
export interface Position {
  symbol: string; quantity: number; cost_basis: number; realized_pnl: number;
}
export interface OrderInfo {
  id: number; account: string; symbol: string; side: 'buy' | 'sell';
  tif: string; order_type: string; stop_price: number; price: number; quantity: number;
  status: string; filled: number; reject_reason: string;
  fills: { price: number; quantity: number }[];
}

async function call<T>(method: string, path: string, body?: unknown): Promise<T> {
  const opts: RequestInit = { method, headers: {} };
  if (body !== undefined) {
    (opts.headers as Record<string, string>)['Content-Type'] = 'application/json';
    opts.body = JSON.stringify(body);
  }
  const res = await fetch(`${API_BASE}${path}`, opts);
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error((data as { error?: string }).error || `HTTP ${res.status}`);
  return data as T;
}

export const getSnapshot = (symbol: string) => call<Snapshot>('GET', `/snapshot/${symbol}`);
export const getInstruments = () =>
  call<{ instruments: { symbol: string; kind: string }[] }>('GET', '/instruments');
export interface MarketRow {
  symbol: string; kind: string; last: number | null; best_bid: number | null; best_ask: number | null;
}
export const getMarkets = () => call<{ markets: MarketRow[] }>('GET', '/markets');
export const getBalance = (account: string) => call<Balance>('GET', `/accounts/${account}/balance`);
export const getPositions = (account: string) =>
  call<{ account: string; positions: Position[] }>('GET', `/accounts/${account}/positions`);
export const getOrders = (account: string) =>
  call<{ account: string; orders: OrderInfo[] }>('GET', `/accounts/${account}/orders`);

export interface CashflowPoint { step: number; txn: string; kind: string; delta: number; balance: number }
export const getCashflow = (account: string) =>
  call<{ account: string; series: CashflowPoint[]; ending_cash: number; funded: number; net_ex_funding: number }>(
    'GET', `/accounts/${account}/cashflow`);

export interface Statement {
  account: string; ending_cash_cents: number; reserved_cents: number;
  cash_postings: { txn: string; delta: number }[];
  trades: { seq: number; symbol: string; side: string; price: number; qty: number }[];
  positions: { symbol: string; qty: number; cost_cents: number; realized_cents: number }[];
}
export const getStatement = (account: string) => call<Statement>('GET', `/accounts/${account}/statement`);
export const getSurveillance = () =>
  call<{ self_trades: { seq: number; account: string; symbol: string; price: number; qty: number }[]; self_trade_count: number }>(
    'GET', '/surveillance');

export const addEquity = (symbol: string) => call('POST', '/instruments/equity', { symbol });
export const fundAccount = (account: string, amount: number) =>
  call('POST', `/accounts/${account}/fund`, { amount });
export const cancelOrder = (id: number) => call('DELETE', `/orders/${id}`);

export interface PlaceOrderReq {
  account: string; symbol: string; side: 'buy' | 'sell';
  quantity: number; price?: number; order_type?: string; tif?: string; stop_price?: number;
}
export const placeOrder = (o: PlaceOrderReq) => call('POST', '/orders', o);

// ---- options ----
export interface OptionContract {
  symbol: string; kind: string; underlying?: string; expiry?: string;
  strike?: number; right?: 'call' | 'put'; multiplier?: number;
}
export const getChain = (underlying: string) =>
  call<{ underlying: string; chain: OptionContract[] }>('GET', `/chain/${underlying}`);
export const addOption = (c: {
  symbol: string; underlying: string; expiry: string; strike: number;
  right: 'call' | 'put'; multiplier?: number;
}) => call('POST', '/instruments/option', c);

export interface GreeksResult {
  account: string;
  net: { delta: number; gamma: number; vega: number; theta: number; rho: number };
  positions: { symbol: string; contracts: number; delta: number; gamma: number; vega: number; theta: number; rho: number }[];
}
export const positionGreeks = (
  account: string, body: { rate?: number; vol?: number; as_of?: string; spots?: Record<string, number> },
) => call<GreeksResult>('POST', `/accounts/${account}/greeks`, body);

export interface ComboLeg { symbol: string; side: 'buy' | 'sell'; price: number; quantity: number }
export const placeCombo = (account: string, legs: ComboLeg[]) =>
  call<{ status: string; reason?: string; legs: number[] }>('POST', '/combos', { account, legs });

export interface StreamEvent {
  type: 'trade' | 'order';
  symbol?: string;
  // order events:
  id?: number; account?: string; side?: 'buy' | 'sell'; status?: string; filled?: number; price?: number;
  // trade events:
  seq?: number; quantity?: number;
}

// Live event stream (Server-Sent Events). Returns the EventSource so the caller can close it.
export function subscribeStream(onEvent: (ev: StreamEvent) => void): EventSource {
  const es = new EventSource(`${API_BASE}/stream`);
  es.onmessage = (e) => {
    try { onEvent(JSON.parse(e.data)); } catch { /* ignore non-JSON heartbeats */ }
  };
  return es;
}
