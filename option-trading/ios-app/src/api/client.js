import AsyncStorage from '@react-native-async-storage/async-storage';

export const DEFAULT_URL = 'http://54.177.77.161';
const TIMEOUT_MS = 8000;

// ── Stored settings ───────────────────────────────────────────────────────────
export async function getBackendUrl() {
  return (await AsyncStorage.getItem('@backend_url')) || DEFAULT_URL;
}
export async function setBackendUrl(url) {
  await AsyncStorage.setItem('@backend_url', url.trim().replace(/\/$/, ''));
}
export async function getApiKey() {
  return (await AsyncStorage.getItem('@api_key')) || '';
}
export async function setApiKey(key) {
  await AsyncStorage.setItem('@api_key', key.trim());
}

// ── Core fetch wrapper ────────────────────────────────────────────────────────
async function _fetch(path, opts = {}) {
  const base   = await getBackendUrl();
  const apiKey = await getApiKey();

  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), TIMEOUT_MS);

  // Build headers — always include API key if configured
  const headers = {
    'Content-Type': 'application/json',
    ...(opts.headers || {}),
  };
  if (apiKey) {
    headers['X-API-Key'] = apiKey;
  }

  try {
    const res = await fetch(`${base}${path}`, {
      ...opts,
      signal: controller.signal,
      headers,
    });
    clearTimeout(timer);
    if (!res.ok) {
      const err = await res.json().catch(() => ({ error: res.statusText }));
      throw { status: res.status, ...err };
    }
    return res.json();
  } catch (e) {
    clearTimeout(timer);
    throw e;
  }
}

// ── API endpoints ─────────────────────────────────────────────────────────────
export const fetchState       = ()                            => _fetch('/api/state');
export const fetchOrders      = ()                            => _fetch('/api/orders');
export const fetchAccount     = ()                            => _fetch('/api/account');
export const fetchNews        = ()                            => _fetch('/api/news');
export const refreshNews      = ()                            => _fetch('/api/news/refresh', { method: 'POST' });
export const fetchChart       = (ticker)                      => _fetch(`/api/chart/${ticker}`);
export const fetchOptionQuote = (ticker, expiry, strike, type) =>
  _fetch(`/api/option_quote/${ticker}/${encodeURIComponent(expiry)}/${strike}/${type}`);
export const placeOrder       = (data)                        =>
  _fetch('/api/order', { method: 'POST', body: JSON.stringify(data) });
export const closePosition    = (tradeId, exitPrice)          =>
  _fetch(`/api/close/${tradeId}`, { method: 'POST', body: JSON.stringify({ exit_price: exitPrice }) });

// ── Connection test (returns { ok, error, unauthorized }) ─────────────────────
export async function testConnection() {
  try {
    await _fetch('/api/account');
    return { ok: true };
  } catch (e) {
    if (e.status === 401) {
      return { ok: false, unauthorized: true, error: 'API key is wrong or missing' };
    }
    return { ok: false, error: e.message || 'Cannot reach server' };
  }
}
