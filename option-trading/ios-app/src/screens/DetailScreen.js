import React, { useState, useEffect, useCallback, useRef } from 'react';
import {
  View, Text, ScrollView, TouchableOpacity, StyleSheet,
  ActivityIndicator, Dimensions, Alert, Modal,
} from 'react-native';
import { PinchGestureHandler, State } from 'react-native-gesture-handler';
import { LineChart } from 'react-native-gifted-charts';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { C } from '../theme';
import { fmtPrice, fmtPct, sentiStrength, sentiColor, agoTs, fmtTs, dte } from '../utils';
import { fetchChart, fetchOptionQuote } from '../api/client';
import { useApp, useNews } from '../AppContext';
import OrderModal from '../components/OrderModal';
import { SentiBars } from '../components/CandidateRow';

const { width: SCREEN_W } = Dimensions.get('window');
const CHART_W = SCREEN_W - 32;

export default function DetailScreen({ route }) {
  const c = route.params?.candidate;
  const { prices } = useApp();
  const newsCtx = useNews();
  const insets  = useSafeAreaInsets();

  const [chartData,    setChartData]    = useState(null);
  const [optQuote,     setOptQuote]     = useState(null);
  const [chartLoad,    setChartLoad]    = useState(true);
  const [optLoad,      setOptLoad]      = useState(true);
  const [orderOpen,    setOrderOpen]    = useState(false);
  const [chartExpand,  setChartExpand]  = useState(false);
  const [chartDays,    setChartDays]    = useState(60);
  const [xScale,       setXScale]       = useState(1);   // zoom X in modal
  const [yZoom,        setYZoom]        = useState(1);   // zoom Y in modal
  const pinchScaleRef  = useRef(1);
  const pinchBaseXRef  = useRef(1);
  const pinchBaseYRef  = useRef(1);

  const isCall    = c?.option_type === 'CALL';
  const typeColor = isCall ? C.green : C.red;

  // ── Live price ───────────────────────────────────────────────────────────
  const liveP    = prices[c?.ticker] || {};
  const curPrice = liveP.price  || c?.price || 0;
  const chgPct   = liveP.change || 0;
  const chgColor = chgPct >= 0 ? C.green : C.red;

  // ── Fetch chart data ──────────────────────────────────────────────────────
  useEffect(() => {
    if (!c) return;
    setChartLoad(true);
    fetchChart(c.ticker)
      .then(data => setChartData(data))
      .catch(() => setChartData(null))
      .finally(() => setChartLoad(false));
  }, [c?.ticker]);

  // ── Fetch option quote ────────────────────────────────────────────────────
  useEffect(() => {
    if (!c) return;
    setOptLoad(true);
    fetchOptionQuote(c.ticker, c.expiry, c.strike, c.option_type)
      .then(data => setOptQuote(data))
      .catch(() => setOptQuote(null))
      .finally(() => setOptLoad(false));
  }, [c?.ticker, c?.expiry, c?.strike, c?.option_type]);

  // ── Build chart series (sliced by selected days) ─────────────────────────
  const chartSeries = useCallback((days = 60) => {
    if (!chartData?.closes?.length) return [];
    return chartData.closes.slice(-days).map(v => ({ value: v }));
  }, [chartData]);

  const sma20Series = useCallback((days = 60) => {
    if (!chartData?.sma20?.length) return [];
    return chartData.sma20.slice(-days).map(v => ({ value: v || 0 }));
  }, [chartData]);

  // ── Y-axis bounds ─────────────────────────────────────────────────────────
  // KEY: in gifted-charts, maxValue = RANGE SIZE (top - bottom), NOT the top price.
  //      yAxisOffset = bottom price.
  //      So the chart draws from yAxisOffset to (yAxisOffset + maxValue).
  //
  // Steps:
  //  1. 5-bar rolling average smooths out single-day spikes
  //  2. pad = 5% of current price (fixed dollar amount each side)
  //  3. yZoom (modal only) shrinks the range inward for vertical zoom
  const chartBounds = useCallback((days = 60, zoom = 1) => {
    const raw = chartData?.closes?.slice(-days) || [];
    if (!raw.length) return {};
    // 5-bar centred rolling average to remove spikes
    const smoothed = raw.map((_, i) => {
      const s = Math.max(0, i - 2);
      const e = Math.min(raw.length - 1, i + 2);
      const w = raw.slice(s, e + 1);
      return w.reduce((a, b) => a + b, 0) / w.length;
    });
    const lo  = Math.min(...smoothed);
    const hi  = Math.max(...smoothed);
    const ref = curPrice || raw[raw.length - 1] || hi;
    const pad = ref * 0.05;
    const mid  = (lo + hi) / 2;
    const half = ((hi - lo) / 2 + pad) / zoom;
    const bottom = Math.floor((mid - half) * 100) / 100;
    const top    = Math.ceil( (mid + half) * 100) / 100;
    // maxValue must be the RANGE, not the top price
    return { yAxisOffset: bottom, maxValue: top - bottom };
  }, [chartData, curPrice]);

  const newsItems = (newsCtx.tickers || {})[c?.ticker] || [];
  const newsSenti = (newsCtx.sentiment || {})[c?.ticker] || 'neutral';

  if (!c) return null;

  return (
    <View style={[styles.container, { paddingBottom: insets.bottom }]}>
      <ScrollView showsVerticalScrollIndicator={false} contentContainerStyle={styles.scroll}>

        {/* ── Header ─────────────────────────────────────────────────────── */}
        <View style={styles.heroCard}>
          <View style={styles.heroLeft}>
            <Text style={styles.heroTicker}>{c.ticker}</Text>
            <View style={[styles.typeBadge, { backgroundColor: typeColor + '22', borderColor: typeColor + '55' }]}>
              <Text style={[styles.typeTxt, { color: typeColor }]}>{c.option_type}</Text>
            </View>
          </View>
          <View style={styles.heroRight}>
            <Text style={[styles.heroPrice, { color: chgColor }]}>${curPrice.toFixed(2)}</Text>
            <Text style={[styles.heroChg, { color: chgColor }]}>
              {chgPct >= 0 ? '+' : ''}{chgPct.toFixed(2)}% today
            </Text>
          </View>
        </View>

        {/* ── Chart ──────────────────────────────────────────────────────── */}
        <View style={styles.card}>
          {/* Header row: title + timeframe tabs + expand */}
          <View style={styles.chartHeader}>
            <Text style={[styles.cardTitle, { marginBottom: 0, flex: 1 }]}>Price Chart</Text>
            <View style={styles.tfTabs}>
              {[7, 30, 60].map(d => (
                <TouchableOpacity
                  key={d}
                  onPress={() => setChartDays(d)}
                  style={[styles.tfTab, chartDays === d && styles.tfTabActive]}
                >
                  <Text style={[styles.tfTabTxt, chartDays === d && { color: C.text }]}>{d}d</Text>
                </TouchableOpacity>
              ))}
            </View>
            {!chartLoad && chartSeries(chartDays).length > 0 && (
              <TouchableOpacity onPress={() => setChartExpand(true)} style={styles.expandBtn}>
                <Text style={styles.expandTxt}>⛶</Text>
              </TouchableOpacity>
            )}
          </View>

          {chartLoad ? (
            <View style={styles.chartLoading}>
              <ActivityIndicator color={C.blue} />
              <Text style={styles.loadingTxt}>Loading chart…</Text>
            </View>
          ) : chartSeries(chartDays).length > 0 ? (
            <View style={{ marginTop: 8 }}>
              <LineChart
                data={chartSeries(chartDays)}
                data2={sma20Series(chartDays).length ? sma20Series(chartDays) : undefined}
                width={CHART_W - 8}
                height={150}
                {...chartBounds(chartDays, 1)}
                color={typeColor}
                color2={C.orange}
                thickness={2}
                thickness2={1.5}
                hideDataPoints
                hideDataPoints2
                noOfSections={4}
                yAxisColor={C.border}
                xAxisColor={C.border}
                yAxisTextStyle={{ color: C.text3, fontSize: 9 }}
                rulesColor={C.border + '44'}
                backgroundColor={C.surface}
                curved
                areaChart
                startFillColor={typeColor + '33'}
                endFillColor={typeColor + '00'}
                startOpacity={0.3}
                endOpacity={0}
              />
              <View style={styles.chartLegend}>
                <View style={[styles.legendDot, { backgroundColor: typeColor }]} />
                <Text style={styles.legendTxt}>Price</Text>
                <View style={[styles.legendDot, { backgroundColor: C.orange, marginLeft: 12 }]} />
                <Text style={styles.legendTxt}>SMA 20</Text>
                <Text style={[styles.legendTxt, { marginLeft: 'auto' }]}>tap ⛶ to expand</Text>
              </View>
            </View>
          ) : (
            <Text style={styles.noData}>Chart data not available</Text>
          )}
        </View>

        {/* ── Expanded chart modal ─────────────────────────────────────────── */}
        <Modal
          visible={chartExpand}
          transparent
          animationType="slide"
          onRequestClose={() => { setChartExpand(false); setXScale(1); setYZoom(1); }}
        >
          <View style={styles.modalOverlay}>
            <View style={styles.modalCard}>
              {/* Header */}
              <View style={{ flexDirection: 'row', alignItems: 'center', marginBottom: 8 }}>
                <Text style={[styles.cardTitle, { flex: 1, marginBottom: 0, color: C.text }]}>
                  {c.ticker}  ·  {chartDays}d
                </Text>
                <TouchableOpacity onPress={() => { setXScale(1); setYZoom(1); }}
                  style={{ marginRight: 14 }}>
                  <Text style={{ color: C.text3, fontSize: 12 }}>Reset</Text>
                </TouchableOpacity>
                <TouchableOpacity onPress={() => { setChartExpand(false); setXScale(1); setYZoom(1); }}>
                  <Text style={{ color: C.blue, fontSize: 15, fontWeight: '600' }}>Done</Text>
                </TouchableOpacity>
              </View>
              {/* Timeframe tabs */}
              <View style={[styles.tfTabs, { marginBottom: 10, alignSelf: 'flex-start' }]}>
                {[7, 30, 60].map(d => (
                  <TouchableOpacity
                    key={d}
                    onPress={() => { setChartDays(d); setXScale(1); setYZoom(1); }}
                    style={[styles.tfTab, chartDays === d && styles.tfTabActive]}
                  >
                    <Text style={[styles.tfTabTxt, chartDays === d && { color: C.text }]}>{d}d</Text>
                  </TouchableOpacity>
                ))}
              </View>
              <Text style={[styles.legendTxt, { marginBottom: 8 }]}>
                Pinch to zoom · scroll to pan
              </Text>
              {/* Pinch-zoomable, horizontally pannable chart */}
              <PinchGestureHandler
                onGestureEvent={(e) => {
                  const s = e.nativeEvent.scale;
                  setXScale(Math.max(1, Math.min(6, pinchBaseXRef.current * s)));
                  setYZoom(Math.max(1, Math.min(8, pinchBaseYRef.current * s)));
                }}
                onHandlerStateChange={(e) => {
                  if (e.nativeEvent.state === State.END ||
                      e.nativeEvent.state === State.CANCELLED) {
                    pinchBaseXRef.current = Math.max(1, Math.min(6, xScale));
                    pinchBaseYRef.current = Math.max(1, Math.min(8, yZoom));
                  }
                }}
              >
                <View>
                  <ScrollView horizontal showsHorizontalScrollIndicator bounces={false}>
                    <LineChart
                      data={chartSeries(chartDays)}
                      data2={sma20Series(chartDays).length ? sma20Series(chartDays) : undefined}
                      width={SCREEN_W * xScale}
                      height={260}
                      {...chartBounds(chartDays, yZoom)}
                      color={typeColor}
                      color2={C.orange}
                      thickness={2}
                      thickness2={1.5}
                      hideDataPoints
                      hideDataPoints2
                      noOfSections={5}
                      yAxisColor={C.border}
                      xAxisColor={C.border}
                      yAxisTextStyle={{ color: C.text3, fontSize: 10 }}
                      rulesColor={C.border + '44'}
                      backgroundColor={C.bg}
                      curved
                      areaChart
                      startFillColor={typeColor + '33'}
                      endFillColor={typeColor + '00'}
                      startOpacity={0.3}
                      endOpacity={0}
                      scrollToEnd
                    />
                  </ScrollView>
                </View>
              </PinchGestureHandler>
            </View>
          </View>
        </Modal>

        {/* ── Trade Summary ───────────────────────────────────────────────── */}
        <View style={styles.card}>
          <Text style={styles.cardTitle}>Trade Summary</Text>
          <View style={styles.metricsGrid}>
            <MetricBox label="Score"   value={`${(c.score||0).toFixed(0)}/100`} color={C.blue} />
            <MetricBox label="R:R"     value={`${(c.rr||0).toFixed(1)}x`}       color={C.purple} />
            <MetricBox label="P(Hit)"  value={`${(c.p_touch||0).toFixed(0)}%`}  color={C.teal} />
            <MetricBox label="IV%"     value={`${(c.iv_pct||0).toFixed(0)}%`}   color={C.orange} />
          </View>

          <View style={styles.sep} />

          {c.bid > 0 && c.ask > 0 ? (
            <Row label="Option Bid / Ask"
                 value={`${fmtPrice(c.bid)} / ${fmtPrice(c.ask)}`}
                 valueColor={C.teal} />
          ) : null}
          <Row label="Entry (mid)"    value={fmtPrice(c.entry)}   valueColor={C.text2} />
          <Row label="Target"         value={fmtPrice(c.target)}  valueColor={C.green} />
          <Row label="Stop"           value={fmtPrice(c.stop)}    valueColor={C.red} />
          <Row label="Strike"         value={`$${(c.strike||0).toFixed(0)}`} />
          <Row label="Expiry"         value={`${c.expiry} (${dte(c.expiry)}d)`} />

          {/* Score bar */}
          <View style={{ marginTop: 12 }}>
            <View style={styles.scoreBarRow}>
              <Text style={styles.scoreBarLabel}>Signal strength</Text>
              <Text style={[styles.scoreBarLabel, { color: typeColor }]}>{(c.score||0).toFixed(0)}/100</Text>
            </View>
            <View style={styles.scoreBarTrack}>
              <View style={[styles.scoreBarFill, { width: `${Math.min(100, c.score||0)}%`, backgroundColor: typeColor }]} />
            </View>
          </View>
        </View>

        {/* ── Option Quote ─────────────────────────────────────────────────── */}
        <View style={styles.card}>
          <Text style={styles.cardTitle}>Live Option Quote</Text>
          {optLoad ? (
            <View style={{ flexDirection: 'row', alignItems: 'center', gap: 8, paddingTop: 8 }}>
              <ActivityIndicator size="small" color={C.blue} />
              <Text style={styles.loadingTxt}>Fetching live quote…</Text>
            </View>
          ) : optQuote ? (
            <>
              <View style={styles.bidAskRow}>
                <BidAskBox label="Bid" value={fmtPrice(optQuote.bid)} color={C.red} />
                <View style={styles.midBox}>
                  <Text style={styles.midLabel}>MID</Text>
                  <Text style={styles.midValue}>{fmtPrice(optQuote.mid)}</Text>
                </View>
                <BidAskBox label="Ask" value={fmtPrice(optQuote.ask)} color={C.green} />
              </View>
              <View style={styles.sep} />
              <Text style={styles.cardSubTitle}>Greeks</Text>
              <View style={styles.greeksRow}>
                <GreekBox label="Delta" value={(optQuote.delta||0).toFixed(2)} />
                <GreekBox label="Theta" value={(optQuote.theta||0).toFixed(3)} color={C.red} />
                <GreekBox label="Vega"  value={(optQuote.vega||0).toFixed(3)}  color={C.orange} />
                <GreekBox label="Gamma" value={(optQuote.gamma||0).toFixed(5)} />
              </View>
              {optQuote.iv ? (
                <Row label="Implied Volatility" value={fmtPct(optQuote.iv * 100)} />
              ) : null}
            </>
          ) : c.bid > 0 && c.ask > 0 ? (
            <>
              <View style={styles.bidAskRow}>
                <BidAskBox label="Bid" value={fmtPrice(c.bid)} color={C.red} />
                <View style={styles.midBox}>
                  <Text style={styles.midLabel}>MID (Entry)</Text>
                  <Text style={styles.midValue}>{fmtPrice(c.entry)}</Text>
                </View>
                <BidAskBox label="Ask" value={fmtPrice(c.ask)} color={C.green} />
              </View>
              <Text style={[styles.noData, { marginTop: 6 }]}>Snapshot from last scan · refresh for live quote</Text>
            </>
          ) : (
            <Text style={styles.noData}>Quote not available — tap refresh to retry</Text>
          )}
        </View>

        {/* ── Stock Analysis ────────────────────────────────────────────────── */}
        <View style={styles.card}>
          <Text style={styles.cardTitle}>📈 Stock Analysis</Text>
          <Row label="Trend"     value={c.trend ? c.trend.charAt(0).toUpperCase() + c.trend.slice(1) : '—'}
               valueColor={c.trend==='bullish'?C.green:c.trend==='bearish'?C.red:C.text2} />
          <Row label="RSI (14)"  value={c.rsi ? `${c.rsi.toFixed(0)} — ${c.rsi>70?'Overbought':c.rsi<30?'Oversold':'Neutral'}` : '—'}
               valueColor={c.rsi>70?C.red:c.rsi<30?C.green:C.text2} />
          {c.sma20  ? <Row label="vs SMA 20"  value={`${curPrice > c.sma20  ? '↑ above' : '↓ below'} $${c.sma20.toFixed(2)}`}  valueColor={curPrice > c.sma20  ? C.green : C.red} /> : null}
          {c.sma50  ? <Row label="vs SMA 50"  value={`${curPrice > c.sma50  ? '↑ above' : '↓ below'} $${c.sma50.toFixed(2)}`}  valueColor={curPrice > c.sma50  ? C.green : C.red} /> : null}
          {c.sma200 ? <Row label="vs SMA 200" value={`${curPrice > c.sma200 ? '↑ above' : '↓ below'} $${c.sma200.toFixed(2)}`} valueColor={curPrice > c.sma200 ? C.green : C.red} /> : null}
          <Row label="ATR (daily)" value={c.atr ? `$${c.atr.toFixed(2)}` : '—'} />
          <Row label="Stock target / stop"
               value={`$${(c.stock_target||c.price_target_stock||0).toFixed(2)} / $${(c.stop_loss_stock||0).toFixed(2)}`}
               valueColor={C.text2} />
        </View>

        {/* ── Reasoning ────────────────────────────────────────────────────── */}
        {c.reasoning?.setup?.trend ? (
          <View style={styles.card}>
            <Text style={styles.cardTitle}>💡 Trade Reasoning</Text>
            {c.reasoning.setup?.trend  ? <Text style={styles.reasonTxt}>• {c.reasoning.setup.trend}</Text>  : null}
            {c.reasoning.setup?.iv     ? <Text style={styles.reasonTxt}>• {c.reasoning.setup.iv}</Text>     : null}
            {c.reasoning.technicals?.rsi_comment ? <Text style={styles.reasonTxt}>• {c.reasoning.technicals.rsi_comment}</Text> : null}
            {c.reasoning.technicals?.macd_comment? <Text style={styles.reasonTxt}>• {c.reasoning.technicals.macd_comment}</Text>: null}
            {(c.reasoning.execution||[]).map((e, i) => (
              <Text key={i} style={[styles.reasonTxt, { color: C.text3 }]}>→ {e}</Text>
            ))}
          </View>
        ) : null}

        {/* ── News ─────────────────────────────────────────────────────────── */}
        <View style={styles.card}>
          <View style={styles.newsHeader}>
            <Text style={styles.cardTitle}>📰 {c.ticker} News</Text>
            <View style={[styles.sentiBadge, { backgroundColor: sentiColor(newsSenti) + '22' }]}>
              <Text style={[styles.sentiBadgeTxt, { color: sentiColor(newsSenti) }]}>
                {newsSenti.toUpperCase()}
              </Text>
            </View>
          </View>
          {newsItems.length === 0 ? (
            <Text style={styles.noData}>No news loaded yet — pull to refresh or check the News tab.</Text>
          ) : (
            newsItems.slice(0, 6).map((n, i) => <NewsRow key={i} article={n} />)
          )}
        </View>

      </ScrollView>

      {/* ── Buy button ───────────────────────────────────────────────────── */}
      <View style={[styles.buyBar, { paddingBottom: insets.bottom + 8 }]}>
        <TouchableOpacity
          style={[styles.buyBtn, { backgroundColor: typeColor }]}
          onPress={() => setOrderOpen(true)}
        >
          <Text style={styles.buyBtnTxt}>
            {isCall ? '▲ Buy CALL Option' : '▼ Buy PUT Option'}
          </Text>
        </TouchableOpacity>
      </View>

      <OrderModal
        visible={orderOpen}
        candidate={c}
        onClose={() => setOrderOpen(false)}
        onSuccess={() => Alert.alert('Order Placed', 'Your order has been submitted successfully.')}
      />
    </View>
  );
}

// ── Sub-components ────────────────────────────────────────────────────────────
function Row({ label, value, valueColor }) {
  return (
    <View style={styles.row}>
      <Text style={styles.rowLabel}>{label}</Text>
      <Text style={[styles.rowValue, valueColor && { color: valueColor }]}>{value || '—'}</Text>
    </View>
  );
}

function MetricBox({ label, value, color }) {
  return (
    <View style={styles.metricBox}>
      <Text style={styles.metricLabel}>{label}</Text>
      <Text style={[styles.metricValue, { color }]}>{value}</Text>
    </View>
  );
}

function BidAskBox({ label, value, color }) {
  return (
    <View style={styles.bidAskBox}>
      <Text style={[styles.bidAskLabel, { color }]}>{label}</Text>
      <Text style={[styles.bidAskValue, { color }]}>{value}</Text>
    </View>
  );
}

function GreekBox({ label, value, color }) {
  return (
    <View style={styles.greekBox}>
      <Text style={styles.greekLabel}>{label}</Text>
      <Text style={[styles.greekValue, color && { color }]}>{value}</Text>
    </View>
  );
}

function NewsRow({ article: n }) {
  const [expanded, setExpanded] = useState(false);
  const str = sentiStrength(n);
  const col = sentiColor(n.sentiment);
  return (
    <TouchableOpacity onPress={() => setExpanded(e => !e)} style={styles.newsRow} activeOpacity={0.8}>
      <View style={styles.newsRowHead}>
        <View style={[styles.newsDot, { backgroundColor: col }]} />
        <Text style={styles.newsTitle} numberOfLines={expanded ? 0 : 2}>{n.title}</Text>
        <SentiBars bars={str.bars} color={str.color} style={{ marginLeft: 8 }} />
      </View>
      <View style={styles.newsMeta}>
        <Text style={styles.newsMetaTxt}>
          {n.publisher ? `${n.publisher} · ` : ''}{n.published ? agoTs(n.published) : ''}
          {n.published ? `  ${fmtTs(n.published)}` : ''}
        </Text>
      </View>
      {expanded && n.summary ? (
        <Text style={styles.newsSummary}>{n.summary}</Text>
      ) : null}
    </TouchableOpacity>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: C.bg },
  scroll:    { padding: 16, paddingBottom: 100 },

  heroCard:   { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12, backgroundColor: C.surface, borderRadius: 14, borderWidth: 1, borderColor: C.border, padding: 16 },
  heroLeft:   { flexDirection: 'row', alignItems: 'center', gap: 10 },
  heroTicker: { fontSize: 28, fontWeight: '900', color: C.text },
  typeBadge:  { borderRadius: 8, borderWidth: 1, paddingHorizontal: 10, paddingVertical: 4 },
  typeTxt:    { fontSize: 11, fontWeight: '700', letterSpacing: 0.5 },
  heroRight:  { alignItems: 'flex-end' },
  heroPrice:  { fontSize: 22, fontWeight: '800' },
  heroChg:    { fontSize: 12, marginTop: 2 },

  card:        { backgroundColor: C.surface, borderRadius: 14, borderWidth: 1, borderColor: C.border, padding: 16, marginBottom: 12 },
  cardTitle:   { fontSize: 11, fontWeight: '700', color: C.text3, textTransform: 'uppercase', letterSpacing: 0.7, marginBottom: 12 },
  cardSubTitle:{ fontSize: 10, fontWeight: '600', color: C.text3, textTransform: 'uppercase', letterSpacing: 0.5, marginTop: 4, marginBottom: 8 },

  chartHeader:  { flexDirection: 'row', alignItems: 'center', marginBottom: 6 },
  tfTabs:       { flexDirection: 'row', gap: 4 },
  tfTab:        { paddingHorizontal: 10, paddingVertical: 4, borderRadius: 8, borderWidth: 1, borderColor: C.border, backgroundColor: C.bg },
  tfTabActive:  { backgroundColor: C.blue + '22', borderColor: C.blue + '88' },
  tfTabTxt:     { fontSize: 11, fontWeight: '600', color: C.text3 },

  chartLoading: { height: 160, alignItems: 'center', justifyContent: 'center', gap: 8 },
  loadingTxt:   { color: C.text3, fontSize: 12 },
  chartLegend:  { flexDirection: 'row', alignItems: 'center', marginTop: 8, paddingHorizontal: 4 },
  legendDot:    { width: 10, height: 10, borderRadius: 5, marginRight: 4 },
  legendTxt:    { fontSize: 10, color: C.text3 },
  noData:       { fontSize: 12, color: C.text3, fontStyle: 'italic', paddingVertical: 8, textAlign: 'center' },
  expandBtn:    { paddingHorizontal: 10, paddingVertical: 4, backgroundColor: C.blue + '22', borderRadius: 8, borderWidth: 1, borderColor: C.blue + '55' },
  expandTxt:    { fontSize: 11, color: C.blue, fontWeight: '600' },
  modalOverlay: { flex: 1, backgroundColor: '#00000099', justifyContent: 'center', padding: 16 },
  modalCard:    { backgroundColor: C.surface, borderRadius: 16, padding: 16, borderWidth: 1, borderColor: C.border },

  metricsGrid: { flexDirection: 'row', gap: 8 },
  metricBox:   { flex: 1, backgroundColor: C.surface2, borderRadius: 10, padding: 10, alignItems: 'center' },
  metricLabel: { fontSize: 9, color: C.text3, textTransform: 'uppercase', letterSpacing: 0.4, marginBottom: 4 },
  metricValue: { fontSize: 15, fontWeight: '700', color: C.text },

  sep:       { height: 1, backgroundColor: C.border + '55', marginVertical: 10 },
  row:       { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', paddingVertical: 7, borderBottomWidth: 1, borderColor: C.border + '33' },
  rowLabel:  { fontSize: 12, color: C.text3 },
  rowValue:  { fontSize: 12, fontWeight: '600', color: C.text },

  scoreBarRow:  { flexDirection: 'row', justifyContent: 'space-between', marginBottom: 4 },
  scoreBarLabel:{ fontSize: 10, color: C.text3 },
  scoreBarTrack:{ height: 4, backgroundColor: C.border + '88', borderRadius: 2, overflow: 'hidden' },
  scoreBarFill: { height: 4, borderRadius: 2 },

  bidAskRow: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between' },
  bidAskBox: { flex: 1, alignItems: 'center', paddingVertical: 10 },
  bidAskLabel:{ fontSize: 10, textTransform: 'uppercase', letterSpacing: 0.5, marginBottom: 4 },
  bidAskValue:{ fontSize: 18, fontWeight: '800' },
  midBox:    { flex: 1.2, alignItems: 'center', backgroundColor: C.surface2, borderRadius: 10, paddingVertical: 10 },
  midLabel:  { fontSize: 9, color: C.text3, textTransform: 'uppercase', letterSpacing: 0.5, marginBottom: 4 },
  midValue:  { fontSize: 22, fontWeight: '900', color: C.teal },

  greeksRow: { flexDirection: 'row', gap: 8 },
  greekBox:  { flex: 1, backgroundColor: C.surface2, borderRadius: 8, padding: 8, alignItems: 'center' },
  greekLabel:{ fontSize: 9, color: C.text3, textTransform: 'uppercase', marginBottom: 3 },
  greekValue:{ fontSize: 12, fontWeight: '700', color: C.text },

  reasonTxt: { fontSize: 12, color: C.text2, lineHeight: 20, marginBottom: 4 },

  newsHeader:    { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', marginBottom: 8 },
  sentiBadge:    { borderRadius: 8, paddingHorizontal: 8, paddingVertical: 3 },
  sentiBadgeTxt: { fontSize: 9, fontWeight: '700', letterSpacing: 0.5 },

  newsRow:     { paddingVertical: 10, borderBottomWidth: 1, borderColor: C.border + '33' },
  newsRowHead: { flexDirection: 'row', alignItems: 'flex-start', gap: 8 },
  newsDot:     { width: 8, height: 8, borderRadius: 4, marginTop: 4, flexShrink: 0 },
  newsTitle:   { flex: 1, fontSize: 12, fontWeight: '600', color: C.text, lineHeight: 18 },
  newsMeta:    { marginTop: 4, paddingLeft: 16 },
  newsMetaTxt: { fontSize: 10, color: C.text3 },
  newsSummary: { fontSize: 11, color: C.text2, lineHeight: 18, marginTop: 6, paddingLeft: 16 },

  buyBar:  { position: 'absolute', bottom: 0, left: 0, right: 0, backgroundColor: C.surface, borderTopWidth: 1, borderColor: C.border, paddingHorizontal: 16, paddingTop: 10 },
  buyBtn:  { borderRadius: 14, height: 52, alignItems: 'center', justifyContent: 'center' },
  buyBtnTxt: { color: '#fff', fontWeight: '800', fontSize: 16 },
});
