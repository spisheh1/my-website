# Options Trader iOS App — Setup Guide

## Requirements
- Node.js 18+ installed on your Mac
- iPhone with the **Expo Go** app installed (free from App Store)
- Your Mac and iPhone on the **same Wi-Fi network**
- The Flask backend (`server.py`) already running

---

## Step 1 — Install Expo Go on your iPhone
Search "Expo Go" in the App Store and install it. It's free.

---

## Step 2 — Install dependencies

Open Terminal, navigate to this folder, and run:

```bash
cd "option trading/ios-app"
npm install
```

---

## Step 3 — Find your Mac's local IP address

In Terminal, run:

```bash
ipconfig getifaddr en0
```

You'll see something like: `192.168.1.42`

---

## Step 4 — Set the backend URL in the app

When the app first opens, go to the **Settings** tab (⚙️) and set the backend URL:

```
http://192.168.1.42:5001
```

Replace `192.168.1.42` with your actual Mac IP from Step 3.

Tap **Test Connection** → you should see "✓ Connected". Tap **Save URL**.

---

## Step 5 — Start the Expo dev server

```bash
npm start
```

A QR code will appear in the Terminal.

---

## Step 6 — Open on your iPhone

1. Open the **Camera** app on your iPhone
2. Point it at the QR code in Terminal
3. Tap the notification that appears — it will open in Expo Go
4. The app will load!

> **Tip:** Shake your iPhone to open the Expo developer menu if needed.

---

## App Screens

| Tab | What it shows |
|-----|--------------|
| 📡 Scanner | Ranked option setups (short/mid/long term), signal bars, scores |
| 💼 Portfolio | Open positions with live P&L, closed trade history |
| 📰 News | Market & per-ticker news with sentiment bars and dates |
| ⚙️ Settings | Backend URL config, connection status |

### Scanner → Detail view
Tap any row to see:
- 60-day price chart with SMA overlay
- Live option bid/ask/mid + Greeks
- Stock analysis (RSI, SMA crossovers, ATR, trend)
- Trade reasoning
- Per-ticker news with sentiment bars
- **Buy button** to place the order

---

## Building a real .ipa (optional — requires Apple Developer account)

```bash
npm install -g eas-cli
eas build --platform ios
```

Follow the prompts. You'll need a paid Apple Developer account ($99/year) to install on a real device outside Expo Go.

---

## Troubleshooting

**"Cannot reach server"**
- Make sure `python server.py` is running on your Mac
- Make sure both devices are on the same Wi-Fi (not guest network)
- Double-check the IP with `ipconfig getifaddr en0`
- Make sure no firewall is blocking port 5001

**Expo Go shows a blank screen**
- Shake your phone → "Reload"
- Re-scan the QR code from Terminal

**Chart not loading**
- This fetches from `/api/chart/<ticker>` — needs yfinance working on the server

**News not loading**
- News loads after the first market scan completes (~30-60s after server start)
- Go to Settings → your connection is active if it shows "Connected & Scanning"
