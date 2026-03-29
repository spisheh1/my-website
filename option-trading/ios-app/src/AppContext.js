import React, { createContext, useContext, useState, useEffect, useRef, useCallback } from 'react';
import { AppState } from 'react-native';
import { fetchState, fetchOrders, fetchNews } from './api/client';

const AppContext = createContext(null);

export function AppProvider({ children }) {
  const [ranked,    setRanked]    = useState({ short: [], mid: [], long: [] });
  const [prices,    setPrices]    = useState({});
  const [optPrices, setOptPrices] = useState({});
  const [orders,    setOrders]    = useState({ open: [], closed: [], account: {} });
  const [news,      setNews]      = useState({ market: [], tickers: {}, sentiment: {} });
  const [scanReady,   setScanReady]   = useState(false);
  const [scanTime,    setScanTime]    = useState(0);
  const [connected,   setConnected]   = useState(false);
  const [loading,     setLoading]     = useState(true);
  const [error,       setError]       = useState(null);
  const [lastRefresh, setLastRefresh] = useState(0);

  const pollRef     = useRef(null);
  const newsPollRef = useRef(null);
  const appStateRef = useRef(AppState.currentState);

  // ── Poll scanner state every 5 s ──────────────────────────────────────────
  const pollState = useCallback(async () => {
    try {
      const data = await fetchState();
      setRanked(data.ranked    || { short: [], mid: [], long: [] });
      setPrices(data.prices    || {});
      setOptPrices(data.opt_prices || {});
      setScanReady(!!data.scan_ready);
      setScanTime(data.scan_time   || 0);
      setConnected(true);
      setError(null);
    } catch (e) {
      setConnected(false);
      setError(e.message || 'Cannot reach server');
    }
  }, []);

  // ── Poll orders every 5 s ─────────────────────────────────────────────────
  const pollOrders = useCallback(async () => {
    try {
      const data = await fetchOrders();
      setOrders({
        open:    data.open    || [],
        closed:  data.closed  || [],
        account: data.account || {},
      });
    } catch (_) {}
  }, []);

  // ── Poll news every 30 s ──────────────────────────────────────────────────
  const pollNews = useCallback(async () => {
    try {
      const data = await fetchNews();
      if (data && (data.market || data.tickers)) {
        setNews({
          market:    data.market    || [],
          tickers:   data.tickers   || {},
          sentiment: data.sentiment || {},
          lastUpdated: data.last_updated || 0,
        });
      }
    } catch (_) {}
  }, []);

  // ── Manual refresh (pull-to-refresh) ─────────────────────────────────────
  const refresh = useCallback(async () => {
    setLoading(true);
    await Promise.all([pollState(), pollOrders(), pollNews()]);
    setLoading(false);
    setLastRefresh(Date.now());
  }, [pollState, pollOrders, pollNews]);

  // ── Initial load + polling intervals ─────────────────────────────────────
  useEffect(() => {
    let alive = true;

    const init = async () => {
      await Promise.all([pollState(), pollOrders(), pollNews()]);
      if (alive) setLoading(false);
    };
    init();

    pollRef.current     = setInterval(() => { pollState(); pollOrders(); }, 5000);
    newsPollRef.current = setInterval(pollNews, 30000);  // every 30 s

    return () => {
      alive = false;
      clearInterval(pollRef.current);
      clearInterval(newsPollRef.current);
    };
  }, []);

  // ── Refresh news when app comes back to foreground ────────────────────────
  useEffect(() => {
    const sub = AppState.addEventListener('change', nextState => {
      if (appStateRef.current.match(/inactive|background/) && nextState === 'active') {
        pollState();
        pollNews();
      }
      appStateRef.current = nextState;
    });
    return () => sub.remove();
  }, [pollState, pollNews]);

  return (
    <AppContext.Provider value={{
      ranked, prices, optPrices, orders, news,
      scanReady, scanTime, connected, loading, error, lastRefresh,
      refresh, pollNews,
    }}>
      {children}
    </AppContext.Provider>
  );
}

export function useApp()    { return useContext(AppContext); }
export function useRanked() { return useContext(AppContext).ranked; }
export function useOrders() { return useContext(AppContext).orders; }
export function useNews()   { return useContext(AppContext).news; }
export function usePrices() { return useContext(AppContext).prices; }
