'use client';

import React, { useEffect, useRef } from 'react';
import { createChart, ISeriesApi, CandlestickData, Time } from 'lightweight-charts';
import { useTradeStore } from '@/store/useTradeStore';

const PriceChart = () => {
  const chartContainerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<any>(null);
  const seriesRef = useRef<ISeriesApi<'Candlestick'>>(null);
  const { trades } = useTradeStore();

  useEffect(() => {
    if (!chartContainerRef.current) return;

    const chart = createChart(chartContainerRef.current, {
      layout: {
        background: { color: '#0a0a0a' },
        textColor: '#d1d4dc',
      },
      grid: {
        vertLines: { color: '#1f1f1f' },
        horzLines: { color: '#1f1f1f' },
      },
      width: chartContainerRef.current.clientWidth,
      height: chartContainerRef.current.clientHeight,
      timeScale: {
        timeVisible: true,
        secondsVisible: true,
      },
    });

    const candlestickSeries = chart.addCandlestickSeries({
      upColor: '#26a69a',
      downColor: '#ef5350',
      borderVisible: false,
      wickUpColor: '#26a69a',
      wickDownColor: '#ef5350',
    });

    chartRef.current = chart;
    seriesRef.current = candlestickSeries;

    const handleResize = () => {
      chart.applyOptions({ width: chartContainerRef.current?.clientWidth });
    };

    window.addEventListener('resize', handleResize);

    return () => {
      window.removeEventListener('resize', handleResize);
      chart.remove();
    };
  }, []);

  // Update chart when new trades come in
  useEffect(() => {
    if (!seriesRef.current || trades.length === 0) return;

    const lastTrade = trades[0];
    const time = Math.floor(Date.now() / 1000) as Time;

    // In a real app, we'd aggregate trades into candles. 
    // Here we'll just update the "current" candle for visualization.
    seriesRef.current.update({
      time,
      open: lastTrade.price,
      high: lastTrade.price,
      low: lastTrade.price,
      close: lastTrade.price,
    } as CandlestickData);
  }, [trades]);

  return <div ref={chartContainerRef} className="w-full h-full" />;
};

export default PriceChart;
