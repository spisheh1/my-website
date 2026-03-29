import React, { useState, memo } from 'react';
import { View, Text, TouchableOpacity, StyleSheet, Linking } from 'react-native';
import { C } from '../theme';
import { sentiStrength, sentiColor, agoTs, fmtTs } from '../utils';
import { SentiBars } from './CandidateRow';

function NewsItem({ article: n }) {
  const [expanded, setExpanded] = useState(false);
  const str     = sentiStrength(n);
  const col     = sentiColor(n.sentiment);
  const hasBody = n.summary && n.summary.length > 10;
  const hasUrl  = n.url && n.url.startsWith('http');

  const openUrl = () => {
    if (hasUrl) Linking.openURL(n.url).catch(() => {});
  };

  return (
    <TouchableOpacity
      style={styles.item}
      onPress={() => setExpanded(e => !e)}
      activeOpacity={0.8}
    >
      {/* Head */}
      <View style={styles.head}>
        <View style={[styles.dot, { backgroundColor: col }]} />
        <Text style={styles.title} numberOfLines={expanded ? 0 : 2}>{n.title}</Text>
        <SentiBars bars={str.bars} color={str.color} style={styles.bars} />
      </View>

      {/* Meta */}
      <View style={styles.meta}>
        {n.publisher ? <Text style={styles.publisher}>{n.publisher}</Text> : null}
        {n.publisher && n.published ? <Text style={styles.metaSep}> · </Text> : null}
        {n.published ? (
          <>
            <Text style={styles.agoTxt}>{agoTs(n.published)}</Text>
            <Text style={styles.dateTxt}> · {fmtTs(n.published)}</Text>
          </>
        ) : null}
      </View>

      {/* Expanded body */}
      {expanded && (
        <View style={styles.body}>
          {hasBody ? <Text style={styles.summary}>{n.summary}</Text> : null}
          {hasUrl ? (
            <TouchableOpacity style={styles.linkBtn} onPress={openUrl}>
              <Text style={styles.linkTxt}>🔗 Read full article ↗</Text>
            </TouchableOpacity>
          ) : null}
        </View>
      )}
    </TouchableOpacity>
  );
}

const styles = StyleSheet.create({
  item: {
    backgroundColor: C.surface, borderRadius: 10, borderWidth: 1,
    borderColor: C.border, padding: 12, marginBottom: 8,
  },
  head:  { flexDirection: 'row', alignItems: 'flex-start', gap: 8, marginBottom: 5 },
  dot:   { width: 8, height: 8, borderRadius: 4, marginTop: 4, flexShrink: 0 },
  title: { flex: 1, fontSize: 12, fontWeight: '600', color: C.text, lineHeight: 18 },
  bars:  { marginTop: 2 },

  meta:      { flexDirection: 'row', alignItems: 'center', flexWrap: 'wrap', paddingLeft: 16 },
  publisher: { fontSize: 10, color: C.text3 },
  metaSep:   { fontSize: 10, color: C.text3 },
  agoTxt:    { fontSize: 10, color: C.text2 },
  dateTxt:   { fontSize: 10, color: C.text3 },

  body:    { marginTop: 8, paddingLeft: 16 },
  summary: { fontSize: 11, color: C.text2, lineHeight: 18, marginBottom: 8 },
  linkBtn: { alignSelf: 'flex-start', borderRadius: 6, borderWidth: 1, borderColor: C.teal + '55', paddingHorizontal: 10, paddingVertical: 4 },
  linkTxt: { fontSize: 10, color: C.teal },
});

export default memo(NewsItem);
