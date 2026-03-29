import React, { useState, useMemo } from 'react';
import {
  View, Text, FlatList, TouchableOpacity,
  StyleSheet, ActivityIndicator, RefreshControl,
} from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { useApp, useRanked, useNews } from '../AppContext';
import CandidateRow from '../components/CandidateRow';
import { C } from '../theme';
import { fmtDate } from '../utils';

const TABS = [
  { key: 'short', label: '7-21d Short' },
  { key: 'mid',   label: '30-60d Mid'  },
  { key: 'long',  label: '90-180d Long' },
];

export default function ScannerScreen({ navigation }) {
  const [activeTab, setActiveTab] = useState('short');
  const { connected, loading, error, scanReady, scanTime, refresh } = useApp();
  const ranked  = useRanked();
  const news    = useNews();
  const insets  = useSafeAreaInsets();

  const candidates = useMemo(
    () => (ranked[activeTab] || []),
    [ranked, activeTab]
  );

  // ── Status bar ───────────────────────────────────────────────────────────
  const statusDot   = connected ? C.green : C.red;
  const statusLabel = connected
    ? (scanReady ? 'Live' : 'Connecting…')
    : (error ? 'Offline' : 'Connecting…');

  return (
    <View style={[styles.container, { paddingBottom: insets.bottom }]}>

      {/* Connection status */}
      <View style={styles.statusBar}>
        <View style={[styles.statusDot, { backgroundColor: statusDot }]} />
        <Text style={styles.statusLabel}>{statusLabel}</Text>
        {scanTime > 0 && (
          <Text style={styles.scanTime}>
            · Scanned {fmtDate(scanTime * 1000)}
          </Text>
        )}
        {!scanReady && connected && (
          <ActivityIndicator size="small" color={C.blue} style={{ marginLeft: 8 }} />
        )}
      </View>

      {/* Timeframe tabs */}
      <View style={styles.tabBar}>
        {TABS.map(t => (
          <TouchableOpacity
            key={t.key}
            style={[styles.tab, activeTab === t.key && styles.tabActive]}
            onPress={() => setActiveTab(t.key)}
          >
            <Text style={[styles.tabText, activeTab === t.key && styles.tabTextActive]}>
              {t.label}
            </Text>
            {(ranked[t.key] || []).length > 0 && (
              <View style={[styles.tabBadge, activeTab === t.key && { backgroundColor: C.blue }]}>
                <Text style={styles.tabBadgeText}>{(ranked[t.key] || []).length}</Text>
              </View>
            )}
          </TouchableOpacity>
        ))}
      </View>

      {/* Content */}
      {!connected && !loading ? (
        <View style={styles.center}>
          <Text style={styles.errorIcon}>📡</Text>
          <Text style={styles.errorTitle}>Cannot reach server</Text>
          <Text style={styles.errorBody}>{error || 'Check that the server is running and you are on the same Wi-Fi.'}</Text>
          <TouchableOpacity style={styles.retryBtn} onPress={refresh}>
            <Text style={styles.retryText}>Retry</Text>
          </TouchableOpacity>
        </View>
      ) : !scanReady && loading ? (
        <View style={styles.center}>
          <ActivityIndicator size="large" color={C.blue} />
          <Text style={[styles.errorBody, { marginTop: 12 }]}>Running first market scan…</Text>
          <Text style={[styles.errorBody, { marginTop: 4, fontSize: 11 }]}>This takes about 30–60 seconds</Text>
        </View>
      ) : candidates.length === 0 ? (
        <View style={styles.center}>
          <Text style={styles.errorIcon}>🔍</Text>
          <Text style={styles.errorTitle}>No candidates</Text>
          <Text style={styles.errorBody}>No high-quality setups found for this timeframe right now.</Text>
          <TouchableOpacity style={styles.retryBtn} onPress={refresh}>
            <Text style={styles.retryText}>Refresh</Text>
          </TouchableOpacity>
        </View>
      ) : (
        <FlatList
          data={candidates}
          keyExtractor={(item, i) => `${item.ticker}-${item.expiry}-${i}`}
          contentContainerStyle={styles.list}
          refreshControl={
            <RefreshControl
              refreshing={loading}
              onRefresh={refresh}
              tintColor={C.blue}
              colors={[C.blue]}
            />
          }
          renderItem={({ item: c }) => (
            <CandidateRow
              candidate={c}
              newsData={news}
              onPress={() => navigation.navigate('Detail', { candidate: c })}
            />
          )}
          ListHeaderComponent={
            <Text style={styles.listHeader}>
              {candidates.length} setup{candidates.length !== 1 ? 's' : ''} ranked by score
            </Text>
          }
        />
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  container:   { flex: 1, backgroundColor: C.bg },
  statusBar:   { flexDirection: 'row', alignItems: 'center', paddingHorizontal: 16, paddingVertical: 8, backgroundColor: C.surface, borderBottomWidth: 1, borderColor: C.border },
  statusDot:   { width: 7, height: 7, borderRadius: 3.5, marginRight: 6 },
  statusLabel: { fontSize: 11, color: C.text2, fontWeight: '600' },
  scanTime:    { fontSize: 10, color: C.text3, marginLeft: 4 },

  tabBar:        { flexDirection: 'row', backgroundColor: C.surface, paddingHorizontal: 12, paddingTop: 8, borderBottomWidth: 1, borderColor: C.border },
  tab:           { flex: 1, flexDirection: 'row', justifyContent: 'center', alignItems: 'center', paddingVertical: 8, borderRadius: 8, gap: 5 },
  tabActive:     { backgroundColor: C.blue + '22' },
  tabText:       { fontSize: 11, fontWeight: '600', color: C.text3 },
  tabTextActive: { color: C.blue },
  tabBadge:      { backgroundColor: C.surface2, borderRadius: 8, paddingHorizontal: 5, paddingVertical: 1 },
  tabBadgeText:  { fontSize: 9, fontWeight: '700', color: C.text3 },

  list:       { padding: 12 },
  listHeader: { fontSize: 11, color: C.text3, marginBottom: 8, paddingLeft: 2 },

  center:     { flex: 1, alignItems: 'center', justifyContent: 'center', padding: 32 },
  errorIcon:  { fontSize: 48, marginBottom: 12 },
  errorTitle: { fontSize: 16, fontWeight: '700', color: C.text, marginBottom: 8, textAlign: 'center' },
  errorBody:  { fontSize: 13, color: C.text3, textAlign: 'center', lineHeight: 20 },
  retryBtn:   { marginTop: 20, backgroundColor: C.blue, borderRadius: 10, paddingHorizontal: 28, paddingVertical: 10 },
  retryText:  { color: '#fff', fontWeight: '700', fontSize: 13 },
});
