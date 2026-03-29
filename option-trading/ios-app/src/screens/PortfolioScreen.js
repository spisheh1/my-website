import React, { useState } from 'react';
import {
  View, Text, FlatList, TouchableOpacity, StyleSheet,
  RefreshControl, ScrollView,
} from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { useApp, useOrders } from '../AppContext';
import PositionCard from '../components/PositionCard';
import { C } from '../theme';
import { fmtPrice, fmtPnl, pnlColor, agoTs, dte } from '../utils';

const TABS = [
  { key: 'open',   label: 'Open Positions' },
  { key: 'closed', label: 'Closed Trades'  },
];

export default function PortfolioScreen() {
  const [tab, setTab]   = useState('open');
  const { loading, refresh } = useApp();
  const orders  = useOrders();
  const insets  = useSafeAreaInsets();

  const acct    = orders.account || {};
  const open    = orders.open    || [];
  const closed  = (orders.closed || []).slice().reverse(); // newest first

  const totalPnlOpen  = open.reduce((s, p) => s + ((p.current_price||p.entry_price||0) - (p.entry_price||0)) * (p.contracts||1) * 100, 0);
  const totalPnlClosed= closed.reduce((s, p) => s + (p.pnl || 0), 0);

  return (
    <View style={[styles.container, { paddingBottom: insets.bottom }]}>

      {/* Account summary */}
      <View style={styles.acctBar}>
        <AcctStat label="Balance"   value={`$${(acct.total_value||0).toLocaleString('en-US', {minimumFractionDigits:2, maximumFractionDigits:2})}`} />
        <AcctStat label="Available" value={`$${(acct.available_cash||0).toLocaleString('en-US', {minimumFractionDigits:2, maximumFractionDigits:2})}`} />
        <AcctStat label="Open P&L"  value={fmtPnl(totalPnlOpen)}  color={pnlColor(totalPnlOpen)} />
        <AcctStat label="All-time"  value={fmtPnl(totalPnlClosed)} color={pnlColor(totalPnlClosed)} />
      </View>

      {/* Tabs */}
      <View style={styles.tabBar}>
        {TABS.map(t => (
          <TouchableOpacity
            key={t.key}
            style={[styles.tab, tab === t.key && styles.tabActive]}
            onPress={() => setTab(t.key)}
          >
            <Text style={[styles.tabTxt, tab === t.key && styles.tabTxtActive]}>
              {t.label}
            </Text>
            <View style={[styles.tabCount, tab === t.key && { backgroundColor: C.blue }]}>
              <Text style={styles.tabCountTxt}>
                {t.key === 'open' ? open.length : closed.length}
              </Text>
            </View>
          </TouchableOpacity>
        ))}
      </View>

      {/* Lists */}
      {tab === 'open' ? (
        open.length === 0 ? (
          <EmptyState
            icon="💼"
            title="No open positions"
            body="Go to the Scanner tab to find and buy option setups."
          />
        ) : (
          <FlatList
            data={open}
            keyExtractor={p => String(p.id)}
            contentContainerStyle={styles.list}
            refreshControl={
              <RefreshControl refreshing={loading} onRefresh={refresh} tintColor={C.blue} />
            }
            renderItem={({ item: p }) => (
              <PositionCard position={p} onClosed={refresh} />
            )}
            ListHeaderComponent={
              <Text style={styles.listHdr}>
                {open.length} open position{open.length !== 1 ? 's' : ''} · Total P&L:{' '}
                <Text style={{ color: pnlColor(totalPnlOpen), fontWeight: '700' }}>
                  {fmtPnl(totalPnlOpen)}
                </Text>
              </Text>
            }
          />
        )
      ) : (
        closed.length === 0 ? (
          <EmptyState icon="📜" title="No closed trades" body="Your trade history will appear here." />
        ) : (
          <FlatList
            data={closed}
            keyExtractor={p => String(p.id)}
            contentContainerStyle={styles.list}
            refreshControl={
              <RefreshControl refreshing={loading} onRefresh={refresh} tintColor={C.blue} />
            }
            renderItem={({ item: p }) => <ClosedRow trade={p} />}
            ListHeaderComponent={
              <Text style={styles.listHdr}>
                {closed.length} closed trade{closed.length !== 1 ? 's' : ''} · All-time P&L:{' '}
                <Text style={{ color: pnlColor(totalPnlClosed), fontWeight: '700' }}>
                  {fmtPnl(totalPnlClosed)}
                </Text>
              </Text>
            }
          />
        )
      )}
    </View>
  );
}

// ── Closed trade row ──────────────────────────────────────────────────────────
function ClosedRow({ trade: p }) {
  const [exp, setExp] = useState(false);
  const isCall   = p.option_type === 'CALL';
  const tColor   = isCall ? C.green : C.red;
  const pnl      = p.pnl || ((p.exit_price||p.entry_price||0) - (p.entry_price||0)) * (p.contracts||1) * 100;
  const pColor   = pnlColor(pnl);
  const closeReason = p.close_reason || p.exit_reason || 'manual';

  return (
    <TouchableOpacity
      style={[styles.closedRow, { borderLeftColor: tColor }]}
      onPress={() => setExp(e => !e)}
      activeOpacity={0.8}
    >
      <View style={styles.closedTop}>
        <View style={{ flexDirection: 'row', alignItems: 'center', gap: 8 }}>
          <Text style={styles.closedTicker}>{p.ticker}</Text>
          <View style={[styles.smallBadge, { backgroundColor: tColor + '22', borderColor: tColor + '55' }]}>
            <Text style={[styles.smallBadgeTxt, { color: tColor }]}>{p.option_type}</Text>
          </View>
          <CloseReasonBadge reason={closeReason} />
        </View>
        <Text style={[styles.closedPnl, { color: pColor }]}>{fmtPnl(pnl)}</Text>
      </View>
      <Text style={styles.closedSub}>
        ${p.strike?.toFixed(0)} · {p.expiry} · {p.contracts||1} contract{p.contracts!==1?'s':''}
      </Text>
      {exp && (
        <View style={styles.closedDetails}>
          <ClosedStat label="Entry"  value={fmtPrice(p.entry_price)} />
          <ClosedStat label="Exit"   value={fmtPrice(p.exit_price)} />
          <ClosedStat label="Return" value={p.entry_price > 0 ? `${(((p.exit_price||0)-(p.entry_price||0))/(p.entry_price||1)*100).toFixed(1)}%` : '—'} valueColor={pColor} />
          <ClosedStat label="Opened" value={p.timestamp ? agoTs(p.timestamp/1000) : '—'} />
        </View>
      )}
    </TouchableOpacity>
  );
}

function CloseReasonBadge({ reason }) {
  const map = {
    target_hit:   { label: '🎯 Target hit', color: C.green },
    stop_hit:     { label: '🛑 Stop hit',   color: C.red },
    manual:       { label: 'Manual close',  color: C.text3 },
    expired:      { label: 'Expired',       color: C.orange },
  };
  const r = map[reason] || { label: reason, color: C.text3 };
  return (
    <View style={[styles.reasonBadge, { borderColor: r.color + '55', backgroundColor: r.color + '11' }]}>
      <Text style={[styles.reasonTxt, { color: r.color }]}>{r.label}</Text>
    </View>
  );
}

function ClosedStat({ label, value, valueColor }) {
  return (
    <View style={styles.closedStat}>
      <Text style={styles.closedStatLabel}>{label}</Text>
      <Text style={[styles.closedStatValue, valueColor && { color: valueColor }]}>{value}</Text>
    </View>
  );
}

function AcctStat({ label, value, color }) {
  return (
    <View style={styles.acctStat}>
      <Text style={styles.acctStatLabel}>{label}</Text>
      <Text style={[styles.acctStatValue, color && { color }]}>{value}</Text>
    </View>
  );
}

function EmptyState({ icon, title, body }) {
  return (
    <View style={styles.empty}>
      <Text style={styles.emptyIcon}>{icon}</Text>
      <Text style={styles.emptyTitle}>{title}</Text>
      <Text style={styles.emptyBody}>{body}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: C.bg },

  acctBar:       { backgroundColor: C.surface, borderBottomWidth: 1, borderColor: C.border, flexDirection: 'row', paddingVertical: 12, paddingHorizontal: 8 },
  acctStat:      { flex: 1, alignItems: 'center' },
  acctStatLabel: { fontSize: 9, color: C.text3, textTransform: 'uppercase', letterSpacing: 0.4, marginBottom: 3 },
  acctStatValue: { fontSize: 12, fontWeight: '700', color: C.text },

  tabBar:       { flexDirection: 'row', backgroundColor: C.surface, paddingHorizontal: 12, paddingTop: 8, borderBottomWidth: 1, borderColor: C.border },
  tab:          { flex: 1, flexDirection: 'row', justifyContent: 'center', alignItems: 'center', paddingVertical: 8, borderRadius: 8, gap: 6 },
  tabActive:    { backgroundColor: C.blue + '22' },
  tabTxt:       { fontSize: 12, fontWeight: '600', color: C.text3 },
  tabTxtActive: { color: C.blue },
  tabCount:     { backgroundColor: C.surface2, borderRadius: 8, paddingHorizontal: 6, paddingVertical: 1 },
  tabCountTxt:  { fontSize: 9, fontWeight: '700', color: C.text3 },

  list:    { padding: 12 },
  listHdr: { fontSize: 11, color: C.text3, marginBottom: 8, paddingLeft: 2 },

  closedRow: {
    backgroundColor: C.surface, borderRadius: 12, borderWidth: 1,
    borderColor: C.border, borderLeftWidth: 4, padding: 12, marginBottom: 8,
  },
  closedTop:    { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 },
  closedTicker: { fontSize: 16, fontWeight: '800', color: C.text },
  closedPnl:    { fontSize: 15, fontWeight: '800' },
  closedSub:    { fontSize: 11, color: C.text3 },
  smallBadge:   { borderRadius: 5, borderWidth: 1, paddingHorizontal: 6, paddingVertical: 1 },
  smallBadgeTxt:{ fontSize: 9, fontWeight: '700' },
  reasonBadge:  { borderRadius: 6, borderWidth: 1, paddingHorizontal: 6, paddingVertical: 1 },
  reasonTxt:    { fontSize: 9, fontWeight: '600' },

  closedDetails: { marginTop: 8, flexDirection: 'row', gap: 8, flexWrap: 'wrap' },
  closedStat:    { backgroundColor: C.surface2, borderRadius: 8, padding: 8, alignItems: 'center', minWidth: 70 },
  closedStatLabel:{ fontSize: 9, color: C.text3, textTransform: 'uppercase', marginBottom: 2 },
  closedStatValue:{ fontSize: 12, fontWeight: '700', color: C.text },

  empty:      { flex: 1, alignItems: 'center', justifyContent: 'center', padding: 40 },
  emptyIcon:  { fontSize: 52, marginBottom: 14 },
  emptyTitle: { fontSize: 16, fontWeight: '700', color: C.text, marginBottom: 8 },
  emptyBody:  { fontSize: 13, color: C.text3, textAlign: 'center', lineHeight: 20 },
});
