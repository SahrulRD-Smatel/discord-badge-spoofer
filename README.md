<p align="center">
  <img src="https://img.shields.io/badge/python-3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python 3.10+"/>
  <img src="https://img.shields.io/badge/platform-Windows-0078D6?style=for-the-badge&logo=windows&logoColor=white" alt="Windows"/>
  <img src="https://img.shields.io/badge/license-MIT-green?style=for-the-badge" alt="MIT License"/>
  <img src="https://img.shields.io/badge/dependencies-zero-brightgreen?style=for-the-badge" alt="Zero Dependencies"/>
</p>

<h1 align="center">🎮 Discord Badge Spoofer</h1>

<p align="center">
  <b>Inflate your Discord profile badges through the <code>/api/v9/science</code> telemetry endpoint.</b><br/>
  <sub>Posts the same events the real Discord client sends — no bots, no libraries, no dependencies.</sub>
</p>

---

## ✨ Features

| Script | Badge Target | Events Used |
|--------|-------------|-------------|
| [`rdiscord.py`](rdiscord.py) | 🎮 **Game Time** & **Game Variety** | `launch_game` + `running_game_heartbeat` |
| [`rstream.py`](rstream.py) | 📺 **Streaming** (Go Live hours) | `stream_start` + `stream_end` |

- **Zero dependencies** — uses only Python standard library (`urllib`, `json`, `uuid`, etc.)
- **DPAPI encryption** — credentials are encrypted with Windows DPAPI, tied to your user account
- **Shared auth** — both scripts use the same `science_state.json`, set up once
- **Batch + retry** — events are sent in batches with automatic retry on network failures
- **Interactive menu** — colored terminal UI with progress tracking
- **Executable fingerprinting** — optional PE fingerprint generation for game badge validation

## 📋 Requirements

- **Python 3.10+**
- **Windows** (DPAPI encryption + fingerprint generation are Windows-specific)
- A Discord account token + `cf_clearance` cookie

## 🚀 Quick Start

```bash
# Clone the repository
git clone https://github.com/SahrulRD-Smatel/discord-badge-spoofer.git
cd discord-badge-spoofer

# Run the game badge spoofer
python rdiscord.py

# Run the streaming badge spoofer
python rstream.py
```

On first run, you'll be prompted for:

1. **Discord Token** — your account token ([how to get it](#-getting-your-token))
2. **Cookie** — the `cf_clearance` cookie header ([how to get it](#-getting-cf_clearance))

Credentials are saved locally in `science_state.json`, encrypted with Windows DPAPI.

## 🎮 Game Badge Spoofer (`rdiscord.py`)

Sends `launch_game` and `running_game_heartbeat` events to credit playtime on Discord-detectable games.

```
  spoofer · discord badges
    by SahrulRD-Smatel

  19:01:28 · loaded 10448 games
  19:01:28 · claimed 20896 games · 20,896h total
  ────────────────────────────────────────────
  19:01:28 · 1 · claim games
  19:01:28 · 2 · refresh auth
  19:01:28 · 3 · set fingerprint
  19:01:28 · 4 · exit
  ────────────────────────────────────────────
```

### Menu Options

| Option | Description |
|--------|-------------|
| `1` | **Claim games** — choose how many games and hours per game to claim |
| `2` | **Refresh auth** — update cookie or re-fetch analytics token |
| `3` | **Set fingerprint** — generate an `executable_fingerprint` from a game `.exe` or running process PID |
| `4` | **Exit** |

### How It Works

Each game session sends 3 events to `/api/v9/science`:

```
1. running_game_heartbeat  (initial=true, duration=0ms)
2. launch_game             (game metadata + fingerprint)
3. running_game_heartbeat  (final=true, duration=Xms)
```

The `duration_tracked_ms` field in the final heartbeat is what credits your playtime.

### Game Badge Tiers

| Hours | Badge |
|------:|-------|
| 1 | Newcomer |
| 15 | Just Starting |
| 50 | Making Progress |
| 100 | Getting Serious |
| 250 | Dedicated |
| 500 | Hardcore |
| 1,000 | Committed |

## 📺 Streaming Badge Spoofer (`rstream.py`)

Sends `stream_start` and `stream_end` events to credit Go Live streaming hours.

```
  spoofer · streaming badge
    by SahrulRD-Smatel

  19:05:00 · tier: Standout · 93h streamed
  19:05:00 · sessions: 150
  ────────────────────────────────────────────
  19:05:00 · 1 · claim streaming hours
  19:05:00 · 2 · refresh auth
  19:05:00 · 3 · view badge tiers
  19:05:00 · 4 · exit
  ────────────────────────────────────────────
```

### Streaming Badge Tiers

| Hours | Badge |
|------:|-------|
| 1 | Newcomer |
| 5 | Fledgling |
| 20 | Breakout |
| 75 | Standout |
| 150 | Trendsetter |
| 300 | Headliner |
| 500 | Star |
| 1,000 | Sensation |
| 2,000 | Visionary |
| 5,000 | Phenomenon |

## 🔑 Getting Your Token

1. Open [Discord Web](https://discord.com/app) in your browser and log in
2. Press **`F12`** to open Developer Tools
3. Go to the **Console** tab
4. If prompted, type `allow pasting` and press Enter
5. Paste this and press Enter:
   ```js
   (webpackChunkdiscord_app.push([[''],{},e=>{m=[];for(let c in e.c)m.push(e.c[c])}]),m).find(m=>m?.exports?.default?.getToken!==void 0).exports.default.getToken()
   ```
6. Copy the token string (without quotes)

## 🍪 Getting cf_clearance

1. In the same Developer Tools, go to the **Application** tab (Chrome/Edge) or **Storage** tab (Firefox)
2. Navigate to **Cookies** → `https://discord.com`
3. Find the cookie named **`cf_clearance`**
4. Copy its **Value**
5. When prompted by the script, paste it as: `cf_clearance=<value>`

Alternatively, go to the **Network** tab, click any request to Discord, and copy the full `cookie:` header value.

## 🔒 Security

- **DPAPI Encryption**: All sensitive fields (`token`, `cookie`, `fingerprint`, `analytics_token`) are encrypted using Windows Data Protection API before being saved to `science_state.json`. The encryption is tied to your Windows user account — even if someone copies the file, they cannot decrypt it on another machine or user account.

- **No external servers**: The scripts only communicate with `discord.com` (for auth and science events) and `cordapi.dolfi.es` (for up-to-date client build numbers, with a local fallback).

## 📁 Project Structure

```
discord-badge-spoofer/
├── rdiscord.py          # Game badge spoofer (playtime + game variety)
├── rstream.py           # Streaming badge spoofer (Go Live hours)
├── science_state.json   # Encrypted auth state (auto-generated)
├── .gitignore
├── LICENSE              # MIT License
└── README.md
```

## ⚠️ Disclaimer

> **This tool interacts with Discord's internal telemetry endpoints in ways not intended by Discord.**
> Using this software may violate Discord's [Terms of Service](https://discord.com/terms).
> Your account may be flagged, restricted, or terminated.
>
> **Use at your own risk. The authors are not responsible for any consequences.**

This project is intended for **educational and research purposes only** — specifically for understanding how Discord's client-side telemetry and badge crediting systems work.

## 📄 License

This project is licensed under the [MIT License](LICENSE).

```
MIT License · Copyright (c) 2026 SahrulRD-Smatel
```

---

<p align="center">
  <sub>made with ☕ by <a href="https://github.com/SahrulRD-Smatel">SahrulRD-Smatel</a></sub>
</p>
