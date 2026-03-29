import React, { useState, useMemo } from 'react';
import {
  View, Text, FlatList, TouchableOpacity, StyleSheet,
  ScrollView, RefreshControl, ActivityIndicator,
} from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { useApp, useNews } from '../AppContext';
import NewsItem from '../components/NewsItem';
import { C } from '../theme';
import { sentiColor, fmtDate } from '../utils';

export default function NewsScreen() {
  const [activeTab, setActiveTab] = useState('market');
  const news      = useNews();
  const { loading, pollNews } = useApp();
  const insets    = useSafeAreaInsets();
  const [refreshing, setRefreshing] = useState(false);

  const marketSenti  = (news.sentiment || {})._market || 'neutral';
  const tickerTabs   = useMemo(() => Object.keys(news.tickers || {}).sort(), [news.tickers]);
  const allTabs      = ['market', ...tickerTabs];

  const items = useMemo(() => {
    if (activeTab === 'market') return news.market || [];
    return (news.tickers || {})[activeTab] || [];
  }, [news, activeTab]);

  const tabSenti = (tab) => {
    if (tab === 'market') return marketSenti;
    return (news.sentiment || {})[tab] || 'neutral';
  };

  const handleRefresh = async () => {
    setRefreshing(true);
    await pollNews();
    setRefreshing(false);
  };

  return (
    <View style={[styles.container, { paddingBottom: insets.bottom }]}>

      {/* Overall sentiment banner */}
      <View style={[styles.banner, { borderLeftColor: sentiColor(marketSenti) }]}>
        <Text style={styles.bannerLabel}>Overall Market</Text>
        <View style={[styles.sentiBadge, { backgroundColor: sentiColor(marketSenti) + '22', borderColor: sentiColor(marketSenti) + '55' }]}>
          <Text style={[styles.sentiBadgeTxt, { color: sentiColor(marketSenti) }]}>
            {marketSenti === 'bullish' ? '▲' : marketSenti === 'bearish' ? '▼' : '●'} {marketSenti.toUpperCase()}
          </Text>
        </View>
        <View style={{ flex: 1 }} />
        <Text style={styles.bannerCount}>{(news.market||[]).length} market articles</Text>
      </View>

      {/* Tab scrollbar */}
      <View style={styles.tabContainer}>
        <ScrollView
          horizontal
          showsHorizontalScrollIndicator={false}
          contentContainerStyle={styles.tabScroll}
        >
          {allTabs.map(tab => {
            const s = tabSenti(tab);
            const col = sentiColor(s);
            return (
              <TouchableOpacity
                key={tab}
                style={[styles.tab, activeTab === tab && { backgroundColor: C.blue, borderColor: C.blue }]}
                onPress={() => setActiveTab(tab)}
              >
                <View style={[styles.tabDot, { backgroundColor: col }]} />
                <Text style={[styles.tabTxt, activeTab === tab && styles.tabTxtActive]}>
                  {tab === 'market' ? '🌐 Market' : tab}
                </Text>
                {tab !== 'market' ? (
                  <Text style={[styles.tabCount, activeTab === tab && { color: '#fff' }]}>
                    {((news.tickers||{})[tab]||[]).length}
                  </Text>
                ) : null}
              </TouchableOpacity>
            );
          })}
        </ScrollView>
      </View>

      {/* News list */}
      {items.length === 0 ? (
        <View style={styles.empty}>
          <ActivityIndicator color={C.blue} />
          <Text style={styles.emptyTxt}>Loading news…</Text>
          <Text style={styles.emptySubTxt}>News loads after the first market scan completes</Text>
          <TouchableOpacity style={styles.refreshBtn} onPress={handleRefresh}>
            <Text style={styles.refreshBtnTxt}>↻ Refresh</Text>
          </TouchableOpacity>
        </View>
      ) : (
        <FlatList
          data={items}
          keyExtractor={(item, i) => `${activeTab}-${i}-${item.title?.slice(0,20)}`}
          contentContainerStyle={styles.list}
          refreshControl={
            <RefreshControl refreshing={refreshing} onRefresh={handleRefresh} tintColor={C.blue} />
          }
          renderItem={({ item }) => <NewsItem article={item} />}
          ListHeaderComponent={
            <View style={styles.listHdr}>
              <Text style={styles.listHdrTxt}>
                {items.length} article{items.length !== 1 ? 's' : ''}
                {activeTab !== 'market' ? ` about ${activeTab}` : ''}
              </Text>
              <SentimentBarSummary items={items} />
            </View>
          }
        />
      )}
    </View>
  );
}

// ── Sentiment summary bar ─────────────────────────────────────────────────────
function SentimentBarSummary({ items }) {
  if (!items.length) return null;
  const bullCount  = items.filter(n => n.sentiment === 'bullish').length;
  const bearCount  = items.filter(n => n.sentiment === 'bearish').length;
  const neutCount  = items.length - bullCount - bearCount;
  const total      = items.length;

  return (
    <View style={styles.sentiSummary}>
      <View style={styles.sentiBarWrap}>
        {bullCount > 0 && (
          <View style={[styles.sentiBarSeg, { flex: bullCount / total, backgroundColor: C.green }]} />
        )}
        {neutCount > 0 && (
          <View style={[styles.sentiBarSeg, { flex: neutCount / total, backgroundColor: C.text3 }]} />
        )}
        {bearCount > 0 && (
          <View style={[styles.sentiBarSeg, { flex: bearCount / total, backgroundColor: C.red }]} />
        )}
      </View>
      <View style={styles.sentiLegend}>
        <LegendDot color={C.green} label={`${bullCount} Bullish`} />
        <LegendDot color={C.text3} label={`${neutCount} Neutral`} />
        <LegendDot color={C.red}   label={`${bearCount} Bearish`} />
      </View>
    </View>
  );
}

function LegendDot({ color, label }) {
  return (
    <View style={{ flexDirection: 'row', alignItems: 'center', gap: 4 }}>
      <View style={{ width: 8, height: 8, borderRadius: 4, backgroundColor: color }} />
      <Text style={{ fontSize: 10, color: C.text3 }}>{label}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: C.bg },

  banner: {
    flexDirection: 'row', alignItems: 'center', gap: 10,
    backgroundColor: C.surface, borderBottomWidth: 1, borderColor: C.border,
    borderLeftWidth: 4, paddingHorizontal: 16, paddingVertical: 10,
  },
  bannerLabel:    { fontSize: 11, color: C.text3 },
  sentiBadge:     { borderRadius: 8, borderWidth: 1, paddingHorizontal: 8, paddingVertical: 3 },
  sentiBadgeTxt:  { fontSize: 10, fontWeight: '700' },
  bannerCount:    { fontSize: 10, color: C.text3 },

  tabContainer: { backgroundColor: C.surface, borderBottomWidth: 1, borderColor: C.border },
  tabScroll:    { paddingHorizontal: 12, paddingVertical: 8, gap: 6 },
  tab:          { flexDirection: 'row', alignItems: 'center', gap: 5, borderRadius: 20, borderWidth: 1, borderColor: C.border, backgroundColor: C.surface, paddingHorizontal: 12, paddingVertical: 6 },
  tabDot:       { width: 6, height: 6, borderRadius: 3 },
  tabTxt:       { fontSize: 11, fontWeight: '600', color: C.text3 },
  tabTxtActive: { color: '#fff' },
  tabCount:     { fontSize: 9, color: C.text3, fontWeight: '700' },

  list:    { padding: 12 },
  listHdr: { marginBottom: 10 },
  listHdrTxt: { fontSize: 11, color: C.text3, marginBottom: 8 },

  sentiSummary:  { backgroundColor: C.surface, borderRadius: 10, borderWidth: 1, borderColor: C.border, padding: 12, marginBottom: 4 },
  sentiBarWrap:  { flexDirection: 'row', height: 8, borderRadius: 4, overflow: 'hidden', marginBottom: 8 },
  sentiBarSeg:   { height: 8 },
  sentiLegend:   { flexDirection: 'row', gap: 14, flexWrap: 'wrap' },

  empty:       { flex: 1, alignItems: 'center', justifyContent: 'center', padding: 32, gap: 10 },
  emptyTxt:    { fontSize: 14, color: C.text2, marginTop: 8 },
  emptySubTxt: { fontSize: 12, color: C.text3, textAlign: 'center', lineHeight: 18 },
  refreshBtn:  { backgroundColor: C.blue + '22', borderRadius: 10, borderWidth: 1, borderColor: C.blue + '55', paddingHorizontal: 20, paddingVertical: 8, marginTop: 8 },
  refreshBtnTxt: { color: C.blue, fontWeight: '700', fontSize: 13 },
});
