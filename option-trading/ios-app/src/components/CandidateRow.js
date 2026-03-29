import React, { memo } from 'react';
import { View, Text, TouchableOpacity, StyleSheet } from 'react-native';
import { C } from '../theme';
import { fmtPrice, sentiStrength, sentiColor, dte } from '../utils';
import { useApp } from '../AppContext';

// ── 5-bar EQ-style signal indicator ──────────────────────────────────────────
function SentiBars({ bars, color, style }) {
  const heights = [4, 6, 8, 10, 12];
  return (
    <View style={[{ flexDirection: 'row', alignItems: 'flex-end', gap: 2 }, style]}>
      {heights.map((h, i) => (
        <View
          key={i}
          style={{
            width:  4,
            height: h,
            borderRadius: 1,
            backgroundColor: i < bars ? color : C.border + '88',
          }}
        />
      ))}
    </View>
  );
}

// ── Score progress bar ────────────────────────────────────────────────────────
function ScoreBar({ score, isCall }) {
  const w = Math.min(100, Math.max(0, score || 0));
  return (
    <View style={styles.scoreWrap}>
      <View style={[styles.scoreFill, {
        width: `${w}%`,
        backgroundColor: isCall ? C.green : C.red,
      }]} />
    </View>
  );
}

// ── Main candidate row ────────────────────────────────────────────────────────
function CandidateRow({ candidate: c, newsData, onPress }) {
  const isCall    = c.option_type === 'CALL';
  const typeColor = isCall ? C.green : C.red;
  const score     = c.score || 0;
  const newsSenti = (newsData?.sentiment || {})[c.ticker] || 'neutral';
  const newsStr   = sentiStrength({ sentiment: newsSenti, title: '', summary: '' });
  const { prices } = useApp();
  const livePrice = (prices[c.ticker] || {}).price || c.price || 0;
  const liveChg   = (prices[c.ticker] || {}).change || 0;

  return (
    <TouchableOpacity style={styles.row} onPress={onPress} activeOpacity={0.7}>

      {/* Left accent bar */}
      <View style={[styles.accent, { backgroundColor: typeColor }]} />

      <View style={styles.body}>
        {/* Top line: ticker + type badge + score */}
        <View style={styles.topLine}>
          <Text style={styles.ticker}>{c.ticker}</Text>
          <View style={[styles.typeBadge, { backgroundColor: typeColor + '22', borderColor: typeColor + '66' }]}>
            <Text style={[styles.typeText, { color: typeColor }]}>{c.option_type}</Text>
          </View>
          <View style={{ flex: 1 }} />
          <Text style={[styles.scoreText, { color: typeColor }]}>{score.toFixed(0)}/100</Text>
        </View>

        {/* Strike + expiry + DTE + stock price */}
        <View style={styles.midLine}>
          <Text style={styles.detailText}>
            ${(c.strike || 0).toFixed(0)} strike · {c.expiry} · {dte(c.expiry)}d
          </Text>
          <View style={styles.stockPriceRow}>
            <Text style={styles.stockPrice}>${livePrice.toFixed(2)}</Text>
            <Text style={[styles.stockChg, { color: liveChg >= 0 ? C.green : C.red }]}>
              {liveChg >= 0 ? '+' : ''}{liveChg.toFixed(2)}%
            </Text>
          </View>
        </View>

        {/* Option Prices — MID big on left, Target+Stop on right */}
        <View style={styles.pricesBlock}>
          <View style={styles.priceMain}>
            <Text style={styles.priceMainLabel}>OPTION MID</Text>
            <Text style={[styles.priceMainValue, { color: C.teal }]}>{fmtPrice(c.entry)}</Text>
            {c.bid > 0 && c.ask > 0 ? (
              <View style={styles.bidAskInline}>
                <Text style={[styles.bidAskSmall, { color: C.red }]}>{fmtPrice(c.bid)}</Text>
                <Text style={styles.bidAskSlash}> / </Text>
                <Text style={[styles.bidAskSmall, { color: C.green }]}>{fmtPrice(c.ask)}</Text>
              </View>
            ) : null}
          </View>
          <View style={styles.priceDivider} />
          <View style={styles.priceSmall}>
            <View style={styles.priceSmallRow}>
              <Text style={styles.priceSmallLabel}>Entry</Text>
              <Text style={[styles.priceSmallValue, { color: C.text }]}>{fmtPrice(c.entry)}</Text>
            </View>
            <View style={styles.priceSmallRow}>
              <Text style={styles.priceSmallLabel}>Target</Text>
              <Text style={[styles.priceSmallValue, { color: C.green }]}>{fmtPrice(c.target)}</Text>
            </View>
            <View style={styles.priceSmallRow}>
              <Text style={styles.priceSmallLabel}>Stop</Text>
              <Text style={[styles.priceSmallValue, { color: C.red }]}>{fmtPrice(c.stop)}</Text>
            </View>
          </View>
        </View>

        {/* Stats row: R:R, P(Hit), Delta, IVR */}
        <View style={styles.statsLine}>
          <Stat label="R:R"    value={`${(c.rr || 0).toFixed(1)}x`} />
          <Stat label="P(Hit)" value={`${(c.p_touch || 0).toFixed(0)}%`} />
          <Stat label="Δ"      value={(c.delta || 0).toFixed(2)} />
          <Stat label="IVR"    value={(c.iv_rank || 0).toFixed(0)} />
        </View>

        {/* Signal bars row */}
        <View style={styles.barsRow}>
          <View style={styles.barGroup}>
            <Text style={styles.barLabel}>Tech</Text>
            <ScoreBar score={score} isCall={isCall} />
          </View>
          <View style={[styles.barGroup, { marginLeft: 12 }]}>
            <Text style={styles.barLabel}>News</Text>
            <View style={styles.newsBarTrack}>
              <View style={{
                height: 3,
                width: `${(newsStr.bars / 5) * 100}%`,
                backgroundColor: sentiColor(newsSenti),
                borderRadius: 2,
              }} />
            </View>
          </View>
          <View style={{ flex: 1 }} />
          <SentiBars bars={newsStr.bars} color={newsStr.color} />
        </View>
      </View>

      {/* Chevron */}
      <Text style={styles.chevron}>›</Text>
    </TouchableOpacity>
  );
}

function PriceChip({ label, value, color }) {
  return (
    <View>
      <Text style={[styles.chipLabel]}>{label}</Text>
      <Text style={[styles.chipValue, { color }]}>{value}</Text>
    </View>
  );
}

function Stat({ label, value }) {
  return (
    <View style={styles.stat}>
      <Text style={styles.statLabel}>{label}</Text>
      <Text style={styles.statValue}>{value}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  row: {
    flexDirection: 'row',
    backgroundColor: C.surface,
    borderRadius: 12,
    borderWidth: 1,
    borderColor: C.border,
    marginBottom: 8,
    overflow: 'hidden',
  },
  accent: { width: 4 },
  body:   { flex: 1, padding: 12 },

  topLine:   { flexDirection: 'row', alignItems: 'center', marginBottom: 4 },
  ticker:    { fontSize: 18, fontWeight: '800', color: C.text, marginRight: 8 },
  typeBadge: { borderRadius: 6, borderWidth: 1, paddingHorizontal: 7, paddingVertical: 2 },
  typeText:  { fontSize: 10, fontWeight: '700', letterSpacing: 0.5 },
  scoreText: { fontSize: 13, fontWeight: '700' },

  midLine:       { marginBottom: 6 },
  detailText:    { fontSize: 11, color: C.text3 },
  stockPriceRow: { flexDirection: 'row', alignItems: 'center', gap: 6, marginTop: 2 },
  stockPrice:    { fontSize: 13, fontWeight: '700', color: C.text },
  stockChg:      { fontSize: 11, fontWeight: '600' },

  pricesBlock:      { flexDirection: 'row', alignItems: 'center', marginBottom: 8,
                       backgroundColor: C.bg + 'cc', borderRadius: 8, padding: 8, gap: 12 },
  priceMain:        { alignItems: 'flex-start' },
  priceMainLabel:   { fontSize: 8, color: C.text3, letterSpacing: 0.8, fontWeight: '600', marginBottom: 2 },
  priceMainValue:   { fontSize: 18, fontWeight: '800' },
  bidAskInline:     { flexDirection: 'row', alignItems: 'baseline', marginTop: 2 },
  bidAskSlash:      { fontSize: 11, color: C.text3, fontWeight: '400' },
  bidAskSmall:      { fontSize: 11, fontWeight: '600' },
  priceDivider:     { width: 1, height: 48, backgroundColor: C.border },
  priceSmall:       { flex: 1, gap: 3 },
  priceSmallRow:    { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' },
  priceSmallLabel:  { fontSize: 10, color: C.text3 },
  priceSmallValue:  { fontSize: 13, fontWeight: '700' },

  statsLine: { flexDirection: 'row', gap: 12, marginBottom: 8 },
  stat:      { alignItems: 'center' },
  statLabel: { fontSize: 9, color: C.text3, textTransform: 'uppercase', letterSpacing: 0.3 },
  statValue: { fontSize: 12, fontWeight: '600', color: C.text2, marginTop: 2 },

  barsRow:   { flexDirection: 'row', alignItems: 'center' },
  barGroup:  { flexDirection: 'row', alignItems: 'center', gap: 6 },
  barLabel:  { fontSize: 9, color: C.text3, textTransform: 'uppercase', letterSpacing: 0.3, width: 30 },
  scoreWrap: { width: 60, height: 3, backgroundColor: C.border + '88', borderRadius: 2, overflow: 'hidden' },
  scoreFill: { height: 3, borderRadius: 2 },
  newsBarTrack: { width: 60, height: 3, backgroundColor: C.border + '88', borderRadius: 2, overflow: 'hidden' },

  chevron: { fontSize: 22, color: C.text3, alignSelf: 'center', paddingRight: 10 },
});

export default memo(CandidateRow);
export { SentiBars };
