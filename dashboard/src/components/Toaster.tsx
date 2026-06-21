'use client';

import React, { useEffect } from 'react';
import { useTradeStore, type Toast } from '@/store/useTradeStore';

const tone: Record<string, string> = {
  filled: 'border-green-500 text-green-300',
  partial: 'border-yellow-500 text-yellow-300',
  canceled: 'border-gray-500 text-gray-300',
  rejected: 'border-red-500 text-red-300',
  info: 'border-blue-500 text-blue-300',
};

const ToastItem = ({ t }: { t: Toast }) => {
  const dismiss = useTradeStore((s) => s.dismissToast);
  useEffect(() => {
    const id = setTimeout(() => dismiss(t.id), 4000);
    return () => clearTimeout(id);
  }, [t.id, dismiss]);
  return (
    <div className={`bg-neutral-900/95 border rounded-md px-3 py-2 text-xs font-mono shadow-lg backdrop-blur cursor-pointer ${tone[t.kind] || tone.info}`}
      onClick={() => dismiss(t.id)}>
      {t.text}
    </div>
  );
};

const Toaster = () => {
  const toasts = useTradeStore((s) => s.toasts);
  return (
    <div className="fixed bottom-4 right-4 z-50 flex flex-col gap-2 items-end">
      {toasts.map((t) => <ToastItem key={t.id} t={t} />)}
    </div>
  );
};

export default Toaster;
