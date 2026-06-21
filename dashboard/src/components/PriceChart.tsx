'use client';

import React, { useEffect, useRef } from 'react';
import {
  createChart, IChartApi, ISeriesApi, CandlestickData, Time, CandlestickSeries,
} from 'lightweight-charts';
import { useTradeStore } from '@/store/useTradeStore';

const BUCKET = 5; // seconds per candle

const PriceChart = () => {
  const containerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const seriesRef = useRef<ISeriesApi<'Candlestick'> | null>(null);
  const candleRef = useRef<CandlestickData | null>(null);
  const { last, selectedSymbol } = useTradeStore();

  useEffect(() => {
    if (!containerRef.current) return;
    const chart = createChart(containerRef.current, {
      layout: { background: { color: '#1a2029' }, textColor: '#8e9cb0' },
      grid: { vertLines: { color: '#2a3340' }, horzLines: { color: '#2a3340' } },
      width: containerRef.current.clientWidth,
      height: containerRef.current.clientHeight,
      timeScale: { timeVisible: true, secondsVisible: true, borderColor: '#323a47' },
      rightPriceScale: { borderColor: '#323a47' },
      crosshair: { mode: 0 },
    });
    const series = chart.addSeries(CandlestickSeries, {
      upColor: '#27b083', downColor: '#e86349', borderVisible: false,
      wickUpColor: '#27b083', wickDownColor: '#e86349',
    });
    chartRef.current = chart;
    seriesRef.current = series;
    const onResize = () => chart.applyOptions({ width: containerRef.current?.clientWidth });
    window.addEventListener('resize', onResize);
    return () => { window.removeEventListener('resize', onResize); chart.remove(); };
  }, []);

  // Reset candles when the symbol changes.
  useEffect(() => {
    candleRef.current = null;
    seriesRef.current?.setData([]);
  }, [selectedSymbol]);

  // Build BUCKET-second OHLC candles from the live last price.
  useEffect(() => {
    if (!seriesRef.current || last == null) return;
    const t = (Math.floor(Date.now() / 1000 / BUCKET) * BUCKET) as Time;
    const cur = candleRef.current;
    let next: CandlestickData;
    if (!cur || cur.time !== t) {
      next = { time: t, open: last, high: last, low: last, close: last };
    } else {
      next = {
        time: t,
        open: cur.open,
        high: Math.max(cur.high, last),
        low: Math.min(cur.low, last),
        close: last,
      };
    }
    candleRef.current = next;
    seriesRef.current.update(next);
  }, [last]);

  return <div ref={containerRef} className="w-full h-full" />;
};

export default PriceChart;
