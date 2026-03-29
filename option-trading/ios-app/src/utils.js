// ── Time helpers ──────────────────────────────────────────────────────────────
export function timeAgo(ms) {
  const sec = Math.floor((Date.now() - ms) / 1000);
  if (sec < 60)    return `${sec}s ago`;
  if (sec < 3600)  return `${Math.floor(sec / 60)}m ago`;
  if (sec < 86400) return `${Math.floor(sec / 3600)}h ago`;
  return `${Math.floor(sec / 86400)}d ago`;
}

export function fmtDate(ms) {
  if (!ms) return '';
  const d = new Date(ms);
  const months = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
  const now = new Date();
  const isToday = d.toDateString() === now.toDateString();
  const h = d.getHours(), m = String(d.getMinutes()).padStart(2, '0');
  const ampm = h >= 12 ? 'PM' : 'AM';
  const h12  = (h % 12) || 12;
  const timeStr = `${h12}:${m} ${ampm}`;
  return isToday ? `Today ${timeStr}` : `${months[d.getMonth()]} ${d.getDate()} · ${timeStr}`;
}

export function fmtTs(unix) { return fmtDate(unix * 1000); }
export function agoTs(unix) { return timeAgo(unix * 1000); }

// ── Number formatting ─────────────────────────────────────────────────────────
export function fmtPrice(v, decimals = 2) {
  if (v == null || isNaN(v)) return '—';
  return `$${Number(v).toFixed(decimals)}`;
}

export function fmtPct(v, decimals = 1) {
  if (v == null || isNaN(v)) return '—';
  return `${Number(v).toFixed(decimals)}%`;
}

export function fmtPnl(v) {
  if (v == null || isNaN(v)) return '—';
  const sign = v >= 0 ? '+' : '';
  return `${sign}$${Math.abs(v).toFixed(2)}`;
}

// ── News sentiment helpers ────────────────────────────────────────────────────
const BULL_KW = new Set([
  'beat','beats','surge','surged','surging','jump','jumped','rally','rallied','record',
  'upgrade','upgraded','buy','strong','strength','growth','profit','gain','gains','rise',
  'rose','soar','soared','climb','climbed','lifted','boost','boosted','bullish','exceed',
  'exceeded','above','outperform','outperformed','positive','recovery','rebound','upside',
  'raises','raised','higher','high','top','increase','increased','improving','breakout',
  'momentum','opportunity',
]);
const BEAR_KW = new Set([
  'miss','missed','misses','drop','dropped','fall','fell','decline','declined','warning',
  'downgrade','downgraded','sell','weak','weakness','loss','losses','cut','cuts','plunge',
  'plunged','concern','concerns','fear','fears','below','bearish','crash','crashed',
  'slump','slumped','disappoint','disappointed','risk','risks','threat','negative',
  'trouble','worry','slowdown','recession','layoff','layoffs','shortage','inflation',
  'tariff','tariffs','uncertainty','lower','worsening','deficit','lawsuit','fraud',
  'investigation','recall','halt','suspended',
]);

export function sentiStrength(article) {
  const words = ((article.title || '') + ' ' + (article.summary || ''))
    .toLowerCase().split(/\W+/);
  const bullC = words.filter(w => BULL_KW.has(w)).length;
  const bearC = words.filter(w => BEAR_KW.has(w)).length;
  const senti = article.sentiment || 'neutral';
  if (senti === 'bullish' || bullC > bearC) {
    return { bars: Math.min(5, Math.max(2, bullC + 1)), color: '#3fb950' };
  }
  if (senti === 'bearish' || bearC > bullC) {
    return { bars: Math.min(5, Math.max(2, bearC + 1)), color: '#f85149' };
  }
  return { bars: 2, color: '#6e7681' };
}

export function sentiColor(s) {
  if (s === 'bullish') return '#3fb950';
  if (s === 'bearish') return '#f85149';
  return '#6e7681';
}

// ── Option/trading helpers ────────────────────────────────────────────────────
export function dte(expiryStr) {
  if (!expiryStr) return 0;
  // Server sends "Apr 10" without year — add current or next year
  let exp = new Date(expiryStr);
  if (isNaN(exp.getTime())) {
    const year = new Date().getFullYear();
    exp = new Date(`${expiryStr} ${year}`);
    if (isNaN(exp.getTime())) return 0;
    // If date already passed this year, use next year
    if (exp < new Date()) exp = new Date(`${expiryStr} ${year + 1}`);
  }
  const now = new Date();
  return Math.max(0, Math.round((exp - now) / 86400000));
}

export function pnlColor(pnl) {
  if (!pnl) return '#6e7681';
  return pnl > 0 ? '#3fb950' : '#f85149';
}
