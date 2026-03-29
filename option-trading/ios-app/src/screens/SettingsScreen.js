import React, { useState, useEffect } from 'react';
import {
  View, Text, TextInput, TouchableOpacity, StyleSheet,
  ScrollView, ActivityIndicator, Alert,
} from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { C } from '../theme';
import {
  getBackendUrl, setBackendUrl,
  getApiKey,    setApiKey,
  testConnection, DEFAULT_URL,
} from '../api/client';
import { useApp } from '../AppContext';

export default function SettingsScreen() {
  const [url,        setUrl]        = useState('');
  const [apiKey,     setApiKeyVal]  = useState('');
  const [showKey,    setShowKey]    = useState(false);
  const [testing,    setTesting]    = useState(false);
  const [testResult, setTestResult] = useState(null);
  const { connected, scanReady, scanTime, lastRefresh } = useApp();
  const insets = useSafeAreaInsets();

  useEffect(() => {
    getBackendUrl().then(u => setUrl(u));
    getApiKey().then(k => setApiKeyVal(k));
  }, []);

  const handleTest = async () => {
    setTesting(true);
    setTestResult(null);
    // Save current values before testing so _fetch picks them up
    await setBackendUrl(url);
    await setApiKey(apiKey);
    const result = await testConnection();
    setTestResult(result);
    setTesting(false);
  };

  const handleSave = async () => {
    if (!url.trim()) return;
    await setBackendUrl(url.trim());
    await setApiKey(apiKey.trim());
    Alert.alert('Saved ✓', 'Settings saved. The app will use these on the next request.');
    setTestResult(null);
  };

  const handleReset = () => {
    setUrl(DEFAULT_URL);
    setApiKeyVal('');
    setTestResult(null);
  };

  return (
    <ScrollView
      style={styles.container}
      contentContainerStyle={[styles.content, { paddingBottom: insets.bottom + 24 }]}
      keyboardShouldPersistTaps="handled"
    >
      {/* ── Connection status ─────────────────────────────────────────── */}
      <View style={styles.statusCard}>
        <View style={styles.statusRow}>
          <View style={[styles.statusDot, { backgroundColor: connected ? C.green : C.red }]} />
          <Text style={styles.statusLabel}>
            {connected
              ? (scanReady ? 'Connected & Scanning' : 'Connected — waiting for scan')
              : 'Disconnected'}
          </Text>
        </View>
        {scanTime    ? <Text style={styles.statusSub}>Last scan: {new Date(scanTime * 1000).toLocaleTimeString()}</Text>    : null}
        {lastRefresh ? <Text style={styles.statusSub}>Last refresh: {new Date(lastRefresh).toLocaleTimeString()}</Text> : null}
      </View>

      {/* ── Server URL ────────────────────────────────────────────────── */}
      <View style={styles.section}>
        <Text style={styles.sectionTitle}>Server URL</Text>
        <Text style={styles.sectionDesc}>
          Local Wi-Fi: use your Mac's IP (run <Text style={styles.mono}>ipconfig getifaddr en0</Text>){'\n'}
          AWS: use your EC2 public IP or domain
        </Text>
        <TextInput
          style={styles.input}
          value={url}
          onChangeText={v => { setUrl(v); setTestResult(null); }}
          placeholder={DEFAULT_URL}
          placeholderTextColor={C.text3}
          autoCapitalize="none"
          autoCorrect={false}
          keyboardType="url"
        />
      </View>

      {/* ── API Key ───────────────────────────────────────────────────── */}
      <View style={styles.section}>
        <Text style={styles.sectionTitle}>API Key  <Text style={styles.badge}>🔐 Required on AWS</Text></Text>
        <Text style={styles.sectionDesc}>
          The secret key that protects your server from public access.
          You set this once on AWS — copy it here exactly.
        </Text>
        <View style={styles.keyRow}>
          <TextInput
            style={[styles.input, { flex: 1, marginBottom: 0 }]}
            value={apiKey}
            onChangeText={v => { setApiKeyVal(v); setTestResult(null); }}
            placeholder="Paste your API key here"
            placeholderTextColor={C.text3}
            autoCapitalize="none"
            autoCorrect={false}
            secureTextEntry={!showKey}
          />
          <TouchableOpacity style={styles.eyeBtn} onPress={() => setShowKey(s => !s)}>
            <Text style={styles.eyeTxt}>{showKey ? '🙈' : '👁'}</Text>
          </TouchableOpacity>
        </View>
        <Text style={styles.keyHint}>Leave blank when running locally (no key needed)</Text>
      </View>

      {/* ── Test result ───────────────────────────────────────────────── */}
      {testResult && (
        <View style={[styles.testResult, { borderColor: testResult.ok ? C.green : C.red }]}>
          <Text style={{ color: testResult.ok ? C.green : C.red, fontSize: 13, fontWeight: '600' }}>
            {testResult.ok
              ? '✓ Connected successfully!'
              : testResult.unauthorized
                ? '✗ Wrong API key — check it matches what\'s on the server'
                : `✗ ${testResult.error || 'Connection failed'}`}
          </Text>
        </View>
      )}

      {/* ── Buttons ───────────────────────────────────────────────────── */}
      <View style={styles.btnRow}>
        <TouchableOpacity
          style={[styles.btn, styles.btnOutline, testing && { opacity: 0.6 }]}
          onPress={handleTest}
          disabled={testing}
        >
          {testing
            ? <ActivityIndicator size="small" color={C.blue} />
            : <Text style={[styles.btnTxt, { color: C.blue }]}>Test Connection</Text>}
        </TouchableOpacity>
        <TouchableOpacity style={[styles.btn, styles.btnPrimary]} onPress={handleSave}>
          <Text style={[styles.btnTxt, { color: '#fff' }]}>Save Settings</Text>
        </TouchableOpacity>
      </View>
      <TouchableOpacity onPress={handleReset} style={styles.resetBtn}>
        <Text style={styles.resetTxt}>Reset to defaults</Text>
      </TouchableOpacity>

      {/* ── How to connect ────────────────────────────────────────────── */}
      <View style={styles.section}>
        <Text style={styles.sectionTitle}>Connection Options</Text>

        <Text style={styles.optionHeader}>📶 Same Wi-Fi (local)</Text>
        <Step n="1" text="Make sure server.py is running on your Mac" />
        <Step n="2" text="Run: ipconfig getifaddr en0  →  copy the IP" />
        <Step n="3" text="Enter: http://192.168.x.x:5001  (no API key needed)" />

        <View style={styles.divider} />

        <Text style={styles.optionHeader}>☁️ AWS (works anywhere)</Text>
        <Step n="1" text="Set up your EC2 server (see the AWS Setup Guide PDF)" />
        <Step n="2" text="Enter: http://your-ec2-ip (port 80, nginx handles routing)" />
        <Step n="3" text="Paste your API key from the setup guide" />
        <Step n="4" text="Tap Test — you should see ✓ Connected" />
      </View>

      {/* ── App info ──────────────────────────────────────────────────── */}
      <View style={styles.section}>
        <Text style={styles.sectionTitle}>App Info</Text>
        <InfoRow label="App version"      value="1.0.0" />
        <InfoRow label="Scanner polling"  value="Every 5 seconds" />
        <InfoRow label="News polling"     value="Every 60 seconds" />
        <InfoRow label="Data source"      value="Yahoo Finance (yfinance)" />
        <InfoRow label="Trade mode"       value="Paper trading (demo)" />
      </View>
    </ScrollView>
  );
}

// ── Sub-components ────────────────────────────────────────────────────────────
function Step({ n, text }) {
  return (
    <View style={styles.step}>
      <View style={styles.stepNum}><Text style={styles.stepNumTxt}>{n}</Text></View>
      <Text style={styles.stepTxt}>{text}</Text>
    </View>
  );
}
function InfoRow({ label, value }) {
  return (
    <View style={styles.infoRow}>
      <Text style={styles.infoLabel}>{label}</Text>
      <Text style={styles.infoValue}>{value}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: C.bg },
  content:   { padding: 16 },

  statusCard:  { backgroundColor: C.surface, borderRadius: 12, borderWidth: 1, borderColor: C.border, padding: 16, marginBottom: 16 },
  statusRow:   { flexDirection: 'row', alignItems: 'center', gap: 8 },
  statusDot:   { width: 9, height: 9, borderRadius: 4.5 },
  statusLabel: { fontSize: 13, fontWeight: '700', color: C.text },
  statusSub:   { fontSize: 11, color: C.text3, marginTop: 4 },

  section:      { backgroundColor: C.surface, borderRadius: 12, borderWidth: 1, borderColor: C.border, padding: 16, marginBottom: 14 },
  sectionTitle: { fontSize: 10, fontWeight: '700', color: C.text3, textTransform: 'uppercase', letterSpacing: 0.7, marginBottom: 8 },
  sectionDesc:  { fontSize: 12, color: C.text2, lineHeight: 18, marginBottom: 12 },
  mono:         { fontFamily: 'monospace', color: C.teal, fontSize: 11 },
  badge:        { fontSize: 10, color: C.orange, fontWeight: '600', textTransform: 'none', letterSpacing: 0 },

  input: {
    backgroundColor: C.surface2, borderRadius: 10, borderWidth: 1,
    borderColor: C.border, color: C.text, padding: 12,
    fontSize: 14, marginBottom: 10,
  },
  keyRow:   { flexDirection: 'row', alignItems: 'center', gap: 8, marginBottom: 6 },
  eyeBtn:   { backgroundColor: C.surface2, borderRadius: 8, width: 44, height: 44, alignItems: 'center', justifyContent: 'center', borderWidth: 1, borderColor: C.border },
  eyeTxt:   { fontSize: 18 },
  keyHint:  { fontSize: 10, color: C.text3, fontStyle: 'italic' },

  testResult: { borderRadius: 10, borderWidth: 1, padding: 12, marginBottom: 12 },

  btnRow:     { flexDirection: 'row', gap: 10, marginBottom: 8 },
  btn:        { flex: 1, borderRadius: 10, height: 46, alignItems: 'center', justifyContent: 'center' },
  btnOutline: { borderWidth: 1, borderColor: C.blue },
  btnPrimary: { backgroundColor: C.blue },
  btnTxt:     { fontWeight: '700', fontSize: 13 },
  resetBtn:   { alignItems: 'center', marginBottom: 20 },
  resetTxt:   { fontSize: 11, color: C.text3 },

  optionHeader: { fontSize: 12, fontWeight: '700', color: C.text, marginBottom: 8, marginTop: 4 },
  divider:      { height: 1, backgroundColor: C.border, marginVertical: 12 },

  step:       { flexDirection: 'row', gap: 10, marginBottom: 8 },
  stepNum:    { width: 20, height: 20, borderRadius: 10, backgroundColor: C.blue + '33', borderWidth: 1, borderColor: C.blue + '66', alignItems: 'center', justifyContent: 'center', flexShrink: 0, marginTop: 1 },
  stepNumTxt: { fontSize: 10, fontWeight: '800', color: C.blue },
  stepTxt:    { flex: 1, fontSize: 12, color: C.text2, lineHeight: 18 },

  infoRow:     { flexDirection: 'row', justifyContent: 'space-between', paddingVertical: 8, borderBottomWidth: 1, borderColor: C.border + '44' },
  infoLabel:   { fontSize: 12, color: C.text3 },
  infoValue:   { fontSize: 12, fontWeight: '600', color: C.text },
});
