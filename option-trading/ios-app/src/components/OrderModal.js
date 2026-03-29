import React, { useState } from 'react';
import {
  Modal, View, Text, TextInput, TouchableOpacity,
  ScrollView, StyleSheet, ActivityIndicator, Alert,
} from 'react-native';
import { C } from '../theme';
import { fmtPrice } from '../utils';
import { placeOrder } from '../api/client';

export default function OrderModal({ visible, candidate: c, onClose, onSuccess }) {
  const [contracts, setContracts] = useState('1');
  const [loading,   setLoading]   = useState(false);

  if (!c) return null;

  const isCall    = c.option_type === 'CALL';
  const typeColor = isCall ? C.green : C.red;
  const numCtrs   = Math.max(1, parseInt(contracts) || 1);
  const totalCost = (c.entry || 0) * numCtrs * 100;
  const maxGain   = ((c.target || 0) - (c.entry || 0)) * numCtrs * 100;
  const maxLoss   = ((c.entry || 0) - (c.stop || 0)) * numCtrs * 100;

  const handleBuy = async () => {
    if (!c) return;
    setLoading(true);
    try {
      await placeOrder({
        ticker:       c.ticker,
        option_type:  c.option_type,
        strike:       c.strike,
        expiry:       c.expiry,
        contracts:    numCtrs,
        entry_price:  c.entry,
        target_price: c.target,
        stop_price:   c.stop,
        stock_target: c.stock_target || c.price_target_stock,
        stock_stop:   c.stop_loss_stock,
      });
      onSuccess?.();
      onClose();
    } catch (e) {
      Alert.alert(
        'Order Failed',
        e.error || e.message || 'Could not place order. Check backend logs.',
        [{ text: 'OK' }]
      );
    } finally {
      setLoading(false);
    }
  };

  return (
    <Modal
      visible={visible}
      animationType="slide"
      presentationStyle="pageSheet"
      onRequestClose={onClose}
    >
      <View style={styles.container}>
        {/* Header */}
        <View style={styles.header}>
          <View>
            <Text style={styles.headerTitle}>Place Order</Text>
            <Text style={styles.headerSub}>{c.ticker} · {c.expiry} · ${(c.strike||0).toFixed(0)} {c.option_type}</Text>
          </View>
          <TouchableOpacity onPress={onClose} style={styles.closeBtn}>
            <Text style={styles.closeTxt}>✕</Text>
          </TouchableOpacity>
        </View>

        <ScrollView style={styles.body} showsVerticalScrollIndicator={false}>

          {/* Type badge */}
          <View style={[styles.typeBadge, { backgroundColor: typeColor + '22', borderColor: typeColor + '55' }]}>
            <Text style={[styles.typeText, { color: typeColor }]}>
              {isCall ? '▲ CALL — Profits if stock rises' : '▼ PUT — Profits if stock falls'}
            </Text>
          </View>

          {/* Key metrics row */}
          <View style={styles.metricsRow}>
            <Metric label="Score"  value={`${(c.score||0).toFixed(0)}/100`} color={C.blue} />
            <Metric label="R:R"    value={`${(c.rr||0).toFixed(1)}x`}       color={C.purple} />
            <Metric label="P(Hit)" value={`${(c.p_touch||0).toFixed(0)}%`}  color={C.teal} />
            <Metric label="Delta"  value={(c.delta||0).toFixed(2)}          color={C.orange} />
          </View>

          {/* Price targets */}
          <View style={styles.section}>
            <Text style={styles.sectionTitle}>Option Price Levels</Text>
            <PriceRow label="Entry (buy at)"        value={fmtPrice(c.entry)}  color={C.text2} />
            <PriceRow label="Target (take profit)"  value={fmtPrice(c.target)} color={C.green} />
            <PriceRow label="Stop (cut loss)"       value={fmtPrice(c.stop)}   color={C.red} />
          </View>

          {/* Contracts input */}
          <View style={styles.section}>
            <Text style={styles.sectionTitle}>Contracts (1 contract = 100 shares)</Text>
            <View style={styles.ctrsRow}>
              <TouchableOpacity
                style={styles.ctrBtn}
                onPress={() => setContracts(String(Math.max(1, numCtrs - 1)))}
              >
                <Text style={styles.ctrBtnTxt}>−</Text>
              </TouchableOpacity>
              <TextInput
                style={styles.ctrsInput}
                value={contracts}
                onChangeText={v => setContracts(v.replace(/[^0-9]/g, ''))}
                keyboardType="number-pad"
                selectTextOnFocus
              />
              <TouchableOpacity
                style={styles.ctrBtn}
                onPress={() => setContracts(String(numCtrs + 1))}
              >
                <Text style={styles.ctrBtnTxt}>+</Text>
              </TouchableOpacity>
            </View>
          </View>

          {/* Order summary */}
          <View style={styles.summary}>
            <Text style={styles.sectionTitle}>Order Summary</Text>
            <PriceRow label="Total cost"     value={`$${totalCost.toFixed(2)}`}   color={C.text} />
            <PriceRow label="Max gain"       value={`+$${maxGain.toFixed(2)}`}    color={C.green} />
            <PriceRow label="Max loss"       value={`-$${Math.abs(maxLoss).toFixed(2)}`} color={C.red} />
            <PriceRow label="Expiry"         value={c.expiry}                     color={C.text2} />
          </View>

          {/* Risk warning */}
          <View style={styles.warning}>
            <Text style={styles.warningText}>
              ⚠️ Options trading involves significant risk. The maximum loss on this trade
              is ${Math.abs(maxLoss).toFixed(2)} if the option expires worthless.
            </Text>
          </View>

        </ScrollView>

        {/* Action buttons */}
        <View style={styles.actions}>
          <TouchableOpacity style={styles.cancelBtn} onPress={onClose} disabled={loading}>
            <Text style={styles.cancelTxt}>Cancel</Text>
          </TouchableOpacity>
          <TouchableOpacity
            style={[styles.buyBtn, { backgroundColor: typeColor }, loading && { opacity: 0.6 }]}
            onPress={handleBuy}
            disabled={loading}
          >
            {loading ? (
              <ActivityIndicator color="#fff" />
            ) : (
              <Text style={styles.buyTxt}>
                {isCall ? '▲ Buy CALL' : '▼ Buy PUT'} · {numCtrs} contract{numCtrs !== 1 ? 's' : ''}
              </Text>
            )}
          </TouchableOpacity>
        </View>
      </View>
    </Modal>
  );
}

function Metric({ label, value, color }) {
  return (
    <View style={styles.metric}>
      <Text style={styles.metricLabel}>{label}</Text>
      <Text style={[styles.metricValue, { color }]}>{value}</Text>
    </View>
  );
}

function PriceRow({ label, value, color }) {
  return (
    <View style={styles.priceRow}>
      <Text style={styles.priceLabel}>{label}</Text>
      <Text style={[styles.priceValue, { color }]}>{value}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: C.bg },

  header: {
    flexDirection: 'row', justifyContent: 'space-between', alignItems: 'flex-start',
    padding: 20, paddingTop: 24,
    backgroundColor: C.surface, borderBottomWidth: 1, borderColor: C.border,
  },
  headerTitle: { fontSize: 18, fontWeight: '800', color: C.text },
  headerSub:   { fontSize: 12, color: C.text3, marginTop: 3 },
  closeBtn:    { backgroundColor: C.surface2, borderRadius: 16, width: 32, height: 32, alignItems: 'center', justifyContent: 'center' },
  closeTxt:    { fontSize: 14, color: C.text2 },

  body: { flex: 1, padding: 16 },

  typeBadge: { borderRadius: 10, borderWidth: 1, padding: 12, marginBottom: 16, alignItems: 'center' },
  typeText:  { fontSize: 13, fontWeight: '700' },

  metricsRow: { flexDirection: 'row', gap: 8, marginBottom: 16 },
  metric:     { flex: 1, backgroundColor: C.surface2, borderRadius: 10, padding: 10, alignItems: 'center' },
  metricLabel: { fontSize: 9, color: C.text3, textTransform: 'uppercase', letterSpacing: 0.5, marginBottom: 4 },
  metricValue: { fontSize: 14, fontWeight: '700' },

  section:      { backgroundColor: C.surface, borderRadius: 10, borderWidth: 1, borderColor: C.border, padding: 14, marginBottom: 12 },
  sectionTitle: { fontSize: 9, color: C.text3, textTransform: 'uppercase', letterSpacing: 0.7, marginBottom: 10 },
  priceRow:     { flexDirection: 'row', justifyContent: 'space-between', paddingVertical: 7, borderBottomWidth: 1, borderColor: C.border + '44' },
  priceLabel:   { fontSize: 12, color: C.text3 },
  priceValue:   { fontSize: 12, fontWeight: '700' },

  ctrsRow:   { flexDirection: 'row', alignItems: 'center', gap: 12 },
  ctrBtn:    { backgroundColor: C.surface2, borderRadius: 8, width: 40, height: 40, alignItems: 'center', justifyContent: 'center' },
  ctrBtnTxt: { fontSize: 20, color: C.text, fontWeight: '600' },
  ctrsInput: {
    flex: 1, backgroundColor: C.surface2, borderRadius: 8, borderWidth: 1,
    borderColor: C.border, color: C.text, textAlign: 'center',
    fontSize: 20, fontWeight: '700', height: 48,
  },

  summary: { backgroundColor: C.surface, borderRadius: 10, borderWidth: 1, borderColor: C.border, padding: 14, marginBottom: 12 },

  warning:     { backgroundColor: '#2a1f0a', borderRadius: 10, borderWidth: 1, borderColor: C.orange + '44', padding: 12, marginBottom: 24 },
  warningText: { fontSize: 11, color: C.orange, lineHeight: 18 },

  actions:    { flexDirection: 'row', gap: 10, padding: 16, paddingBottom: 32, backgroundColor: C.surface, borderTopWidth: 1, borderColor: C.border },
  cancelBtn:  { flex: 1, backgroundColor: C.surface2, borderRadius: 12, height: 50, alignItems: 'center', justifyContent: 'center', borderWidth: 1, borderColor: C.border },
  cancelTxt:  { color: C.text2, fontWeight: '700', fontSize: 14 },
  buyBtn:     { flex: 2, borderRadius: 12, height: 50, alignItems: 'center', justifyContent: 'center' },
  buyTxt:     { color: '#fff', fontWeight: '800', fontSize: 14 },
});
