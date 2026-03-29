import React, { useState } from 'react';
import { View, Text, TouchableOpacity, StyleSheet, Alert, ActivityIndicator } from 'react-native';
import { C } from '../theme';
import { fmtPrice, fmtPnl, pnlColor, agoTs, dte } from '../utils';
import { closePosition } from '../api/client';

export default function PositionCard({ position: p, onClosed }) {
  const [loading, setLoading] = useState(false);
  const [expanded, setExpanded] = useState(false);

  const isCall    = p.option_type === 'CALL';
  const typeColor = isCall ? C.green : C.red;

  const entry   = p.entry_price   || 0;
  const current = p.current_price || entry;
  const target  = p.target_price  || 0;
  const stop    = p.stop_price    || 0;
  const ctrs    = p.contracts     || 1;

  const pnl     = (current - entry) * ctrs * 100;
  const pnlPct  = entry > 0 ? ((current - entry) / entry * 100) : 0;
  const pColor  = pnlColor(pnl);

  // Progress bar: from stop → target
  const range    = target - stop;
  const progress = range > 0 ? Math.max(0, Math.min(100, ((current - stop) / range) * 100)) : 50;

  const handleClose = () => {
    Alert.alert(
      'Close Position',
      `Close ${p.ticker} ${p.option_type} at $${current.toFixed(2)}?\nP&L: ${fmtPnl(pnl)}`,
      [
        { text: 'Cancel', style: 'cancel' },
        {
          text: 'Close Position',
          style: 'destructive',
          onPress: async () => {
            setLoading(true);
            try {
              await closePosition(p.id, current);
              onClosed?.();
            } catch (e) {
              Alert.alert('Error', e.error || 'Could not close position');
            } finally {
              setLoading(false);
            }
          },
        },
      ]
    );
  };

  return (
    <TouchableOpacity
      style={[styles.card, { borderLeftColor: typeColor }]}
      onPress={() => setExpanded(e => !e)}
      activeOpacity={0.85}
    >
      {/* Top row */}
      <View style={styles.topRow}>
        <View style={styles.topLeft}>
          <Text style={styles.ticker}>{p.ticker}</Text>
          <View style={[styles.badge, { backgroundColor: typeColor + '22', borderColor: typeColor + '55' }]}>
            <Text style={[styles.badgeTxt, { color: typeColor }]}>{p.option_type}</Text>
          </View>
        </View>
        <View style={styles.topRight}>
          <Text style={[styles.pnl, { color: pColor }]}>{fmtPnl(pnl)}</Text>
          <Text style={[styles.pnlPct, { color: pColor }]}>
            {pnlPct >= 0 ? '+' : ''}{pnlPct.toFixed(1)}%
          </Text>
        </View>
      </View>

      {/* Strike / expiry */}
      <Text style={styles.sub}>
        ${p.strike?.toFixed(0)} strike · {p.expiry} · {dte(p.expiry)}d remaining
      </Text>

      {/* Option prices */}
      <View style={styles.priceRow}>
        <PricePill label="Entry"   value={fmtPrice(entry)}   color={C.text2} />
        <PricePill label="Current" value={fmtPrice(current)} color={pColor} />
        <PricePill label="Target"  value={fmtPrice(target)}  color={C.green} />
        <PricePill label="Stop"    value={fmtPrice(stop)}    color={C.red} />
      </View>

      {/* Progress bar */}
      <View style={styles.progressWrap}>
        <View style={[styles.progressFill, {
          width: `${progress}%`,
          backgroundColor: pnl >= 0 ? C.green : C.red,
        }]} />
      </View>
      <View style={styles.progressLabels}>
        <Text style={styles.progressLabel}>Stop {fmtPrice(stop)}</Text>
        <Text style={[styles.progressLabel, { color: pColor, fontWeight: '700' }]}>
          {current.toFixed(2)}
        </Text>
        <Text style={styles.progressLabel}>Target {fmtPrice(target)}</Text>
      </View>

      {/* Expanded details */}
      {expanded && (
        <View style={styles.details}>
          <View style={styles.sep} />
          <DetailRow label="Contracts"    value={`${ctrs}x`} />
          <DetailRow label="Cost basis"   value={`$${(entry * ctrs * 100).toFixed(2)}`} />
          <DetailRow label="Current val"  value={`$${(current * ctrs * 100).toFixed(2)}`} />
          <DetailRow label="Opened"       value={p.timestamp ? agoTs(p.timestamp / 1000) : '—'} />
          {p.mode === 'paper' && (
            <View style={styles.paperBadge}>
              <Text style={styles.paperTxt}>PAPER TRADE</Text>
            </View>
          )}
          <TouchableOpacity
            style={[styles.closeBtn, loading && { opacity: 0.6 }]}
            onPress={handleClose}
            disabled={loading}
          >
            {loading ? (
              <ActivityIndicator color={C.red} size="small" />
            ) : (
              <Text style={styles.closeBtnTxt}>Close Position</Text>
            )}
          </TouchableOpacity>
        </View>
      )}
    </TouchableOpacity>
  );
}

function PricePill({ label, value, color }) {
  return (
    <View style={styles.pricePill}>
      <Text style={styles.pillLabel}>{label}</Text>
      <Text style={[styles.pillValue, { color }]}>{value}</Text>
    </View>
  );
}

function DetailRow({ label, value }) {
  return (
    <View style={styles.detailRow}>
      <Text style={styles.detailLabel}>{label}</Text>
      <Text style={styles.detailValue}>{value}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  card: {
    backgroundColor: C.surface, borderRadius: 14, borderWidth: 1,
    borderColor: C.border, borderLeftWidth: 4, padding: 14, marginBottom: 10,
  },
  topRow:  { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 4 },
  topLeft: { flexDirection: 'row', alignItems: 'center', gap: 8 },
  ticker:  { fontSize: 18, fontWeight: '800', color: C.text },
  badge:   { borderRadius: 6, borderWidth: 1, paddingHorizontal: 7, paddingVertical: 2 },
  badgeTxt:{ fontSize: 10, fontWeight: '700' },
  topRight:{ alignItems: 'flex-end' },
  pnl:     { fontSize: 16, fontWeight: '800' },
  pnlPct:  { fontSize: 11, marginTop: 1 },
  sub:     { fontSize: 11, color: C.text3, marginBottom: 10 },

  priceRow: { flexDirection: 'row', gap: 8, marginBottom: 10 },
  pricePill:{ flex: 1, backgroundColor: C.surface2, borderRadius: 8, padding: 8, alignItems: 'center' },
  pillLabel:{ fontSize: 9, color: C.text3, textTransform: 'uppercase', marginBottom: 2 },
  pillValue:{ fontSize: 11, fontWeight: '700' },

  progressWrap:   { height: 6, backgroundColor: C.surface2, borderRadius: 3, overflow: 'hidden' },
  progressFill:   { height: 6, borderRadius: 3 },
  progressLabels: { flexDirection: 'row', justifyContent: 'space-between', marginTop: 4 },
  progressLabel:  { fontSize: 9, color: C.text3 },

  details:   { marginTop: 4 },
  sep:       { height: 1, backgroundColor: C.border + '55', marginVertical: 10 },
  detailRow: { flexDirection: 'row', justifyContent: 'space-between', paddingVertical: 5, borderBottomWidth: 1, borderColor: C.border + '33' },
  detailLabel:{ fontSize: 11, color: C.text3 },
  detailValue:{ fontSize: 11, fontWeight: '600', color: C.text },

  paperBadge: { backgroundColor: C.orange + '22', borderRadius: 6, borderWidth: 1, borderColor: C.orange + '55', alignSelf: 'flex-start', paddingHorizontal: 8, paddingVertical: 3, marginTop: 8 },
  paperTxt:   { fontSize: 9, color: C.orange, fontWeight: '700', letterSpacing: 0.5 },

  closeBtn:    { marginTop: 12, backgroundColor: C.red + '22', borderRadius: 10, borderWidth: 1, borderColor: C.red + '44', height: 40, alignItems: 'center', justifyContent: 'center' },
  closeBtnTxt: { color: C.red, fontWeight: '700', fontSize: 13 },
});
