<p align="center">
  <img src="https://img.shields.io/badge/python-3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python 3.10+"/>
  <img src="https://img.shields.io/badge/platform-Windows-0078D6?style=for-the-badge&logo=windows&logoColor=white" alt="Windows"/>
  <img src="https://img.shields.io/badge/security-DPAPI%20Encrypted-success?style=for-the-badge&logo=shield" alt="DPAPI Encrypted"/>
  <img src="https://img.shields.io/badge/architecture-zero--dependencies-brightgreen?style=for-the-badge" alt="Zero Dependencies"/>
  <img src="https://img.shields.io/badge/license-MIT-green?style=for-the-badge" alt="MIT License"/>
</p>

<h1 align="center">🎮 Discord Badge Spoofer & Telemetry Engine</h1>

<p align="center">
  <b>High-fidelity, production-grade telemetry spoofer for Discord profile badges.</b><br/>
  <sub>Architected with zero external dependencies, OS-level DPAPI encryption, resilient network fault-tolerance, and precise PE32+ telemetry fingerprinting.</sub>
</p>

---

## 🌟 Why This Implementation Stands Out

Unlike typical open-source spoofer scripts that store plain-text tokens or inject forced promo gates, this repository was engineered with **enterprise-grade software engineering and cybersecurity practices**:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           ARCHITECTURE OVERVIEW                             │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│   [ Credential Ingestion ] ──────► [ Windows DPAPI CryptProtectData ]       │
│                                                │                            │
│                                                ▼                            │
│   [ Discord /science API ] ◄──── [ Resilient Retry Queue (3x Backoff) ]    │
│            ▲                                   ▲                            │
│            │                                   │                            │
│   [ Dynamic SuperProps ]               [ Batch Engine (50/chunk) ]          │
│   (cordapi + local fallback)                   ▲                            │
│                                                │                            │
│   [ PE32+ Authenticode Hash ] ──► [ Telemetry Payload Generator ]           │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 📊 Engineering Benchmark: Our Engine vs Generic Scripts

| Metric / Aspect | 🚀 Our Engine (`rdiscord.py` / `rstream.py`) | ⚠️ Generic / Naive Scripts |
|:---|:---|:---|
| **Credential Security** | 🔒 **Windows DPAPI (`CryptProtectData`)**<br/>Cryptographically tied to your OS user SID; unreadable if stolen. | ❌ **Plaintext JSON / ENV**<br/>Easily harvested by malware, infostealers, or token-loggers. |
| **Dependency Footprint** | ⚡ **Zero Dependencies**<br/>Pure Python 3.10+ standard library (`urllib`, `ctypes`, `dataclasses`). Zero supply-chain attack risk. | ❌ Heavy pip installs (`requests`, `pycryptodome`, etc.) prone to deprecation & CVEs. |
| **Network Resilience** | 🔁 **Smart Exponential Backoff**<br/>Automated 3-tier retry strategy against transient SSL drops and Discord rate limits. | ❌ **Zero Retries**<br/>Single timeout drops entire batches and desyncs state. |
| **Telemetry Fidelity** | 🎯 **Authentic PE32+ Fingerprinting**<br/>Native Win32 Authenticode hashing (`CryptHashPublicKeyInfo`, Section hashes, MachineGuid). | ❌ Omitted or fake static fingerprints, easily filtered by Discord telemetry lakes. |
| **Protocol Parity** | 🔄 **Dynamic Super-Properties**<br/>Live client build resolution with intelligent offline fallback. | ❌ Hardcoded client versions that get instantly flagged as stale. |
| **User Experience** | 💎 **Clean, Modular CLI**<br/>No forced subscriptions, no adware, zero artificial delays. | ❌ Adware gates (forced YouTube subscriptions & Discord invites). |

---

## ✨ Core Features

| Module | Badge Target | Protocol Events Emulated |
|---|---|---|
| [`rdiscord.py`](rdiscord.py) | 🗡️ **Game Time** (Playtime) & 🎮 **Game Variety** (Unique Games) | `running_game_heartbeat` ➔ `launch_game` ➔ `running_game_heartbeat` |
| [`rstream.py`](rstream.py) | 🖥️ **Streaming** (Go Live Hours) | `stream_start` ➔ `stream_end` (with real server snowflakes) |
| [`hypesquad.js`](hypesquad.js) | 💜 **HypeSquad Houses** (Bravery / Brilliance / Balance) | Direct DevTools Console REST injection (`POST /hypesquad/online`) |
| [`valorant_rpc.py`](valorant_rpc.py) | 👑 **VALORANT Radiant Rank Card** (Top 500 & RR) | Local Named Pipe IPC (`SET_ACTIVITY` via `\\.\pipe\discord-ipc-0`) |

- **🛡️ OS-Bound Cryptographic Vault**: Credentials (`token`, `cookie`, `fingerprint`, `analytics_token`) are encrypted with Windows DPAPI before hitting disk.
- **⚡ Batch Pipeline Processing**: Chunked telemetry ingestion (`BATCH_SIZE = 50`) optimized for Discord's analytics throughput.
- **🔄 Session State Synchronization**: Self-healing auth lifecycle with automatic token refresh (`AUTH_MAX_AGE = 12h`).
- **🕹️ Comprehensive Detectable Database**: Automatically fetches and caches Discord's 10,000+ official detectable games.
- **🖥️ High-Precision Executable Fingerprinter**: Emulates Discord's proprietary desktop binary scanner to generate legit PE signatures.

---

## 🛠️ System Architecture & Engineering Patterns

### 1. Cryptographic Protection via Windows DPAPI
Credentials never rest in plaintext. By invoking Windows `CryptProtectData` via Python `ctypes`, ciphertext is encrypted using keys derived from the logged-in Windows user's password and TPM:
```python
# Low-level Win32 CryptoAPI Integration
import ctypes
import ctypes.wintypes

def _dpapi_encrypt(plaintext: str) -> str:
    # Encrypts payload bound to Windows User SID
    ...
    ctypes.windll.crypt32.CryptProtectData(...)
```

### 2. Fault-Tolerant Exponential Backoff Dispatcher
Transient network interruptions and socket resets are intercepted and retried gracefully:
```python
for attempt in range(3):
    status = self.client.post(events)
    if status in (204, 401, 403):
        break
    delay = BATCH_DELAY * (attempt + 2)
    time.sleep(delay)  # Exponential backoff
```

### 3. State Management & Zero-Repeat Rotation
The engine utilizes a deterministic set rotation algorithm over Discord's 10,400+ game catalog, guaranteeing that repeated runs maximize variety without inflating duplicate IDs prematurely.

---

## 📋 Prerequisites

- **OS**: Windows 10 / 11 (required for DPAPI and Win32 PE fingerprint generation)
- **Runtime**: Python 3.10 or higher
- **Credentials**: Your Discord account authorization token & `cf_clearance` cookie

---

## 🚀 Quick Start

### 1. Installation

```bash
# Clone repository
git clone https://github.com/SahrulRD-Smatel/discord-badge-spoofer.git
cd discord-badge-spoofer

# Launch the game badge engine
python rdiscord.py

# Or launch the streaming badge engine
python rstream.py
```

### 2. First Run Setup

On first launch, you will be prompted for:
1. **Discord Account Token** ([How to extract](#-extracting-your-token))
2. **Cloudflare `cf_clearance` Cookie** ([How to extract](#-extracting-cf_clearance))

All credentials are saved locally in encrypted form into [`science_state.json`](science_state.json).

---

## 🎮 CLI Showcase & Operations

```
  spoofer · discord badges
    by SahrulRD-Smatel

  06:20:00 · loaded 10448 games
  06:20:00 · claimed 20896 games · 20,896h total
  ────────────────────────────────────────────
  06:20:00 · 1 · claim games
  06:20:00 · 2 · refresh auth
  06:20:00 · 3 · set fingerprint
  06:20:00 · 4 · exit
  ────────────────────────────────────────────
```

### Menu Actions

1. **Claim Games / Hours**: Select quantity of games and duration (`hours_per_game`) to simulate.
2. **Refresh Auth**: Manually refresh `analytics_token` or update expired `cf_clearance` cookies.
3. **Set Fingerprint**: Point the tool at any real PE32+ binary (`.exe`) or running process PID to generate legitimate telemetry fingerprints.
4. **Exit**: Gracefully persist session state and terminate.

---

## 💜 HypeSquad House Claimer (`hypesquad.js`)

Unlike game and streaming telemetry which require backend batch processing delays, the **HypeSquad House Badge** can be claimed or switched **instantly** without taking the in-app quiz:

### Quick Instructions:
1. Open Discord in your Desktop App or Web Browser (`discord.com/app`).
2. Press **`F12`** (or `Ctrl + Shift + I`) to open Developer Tools and switch to the **Console** tab.
3. If prompted by Discord, type `allow pasting` and press Enter.
4. Copy the script from [`hypesquad.js`](hypesquad.js) (or the compact snippet below), set your desired house ID, and press Enter:

```javascript
// House IDs: 1 = Bravery (Purple 💜) | 2 = Brilliance (Red ❤️) | 3 = Balance (Teal 💚)
(async (h=1)=>{const w=window.webpackChunkdiscord_app.push([[Symbol()],{},r=>r]);window.webpackChunkdiscord_app.pop();const m=w.m,c=w.c;const f=s=>{for(const[i,o]of Object.entries(m))if(o.toString().includes(s))return c[i]?.exports};const k=(e,p)=>{if(!e)return null;for(const x in e)if(e[x]&&e[x][p])return e[x];return null};const api=k(f('.set("X-Audit-Log-Reason",'),"patch");if(!api?.post)return console.error("API client not found");await api.post({url:"/hypesquad/online",body:{house_id:h}});console.log("✅ HypeSquad badge updated! Press Ctrl+R to refresh.")})(1);
```
5. Press **`Ctrl + R`** to immediately view your new badge!

---

## 👑 VALORANT Radiant Rank RPC Spoofer (`valorant_rpc.py`)

Display real-time **Radiant / Immortal** rank, dynamic live match score progression (`0-0` ➔ `13`), active competitive map pool rotation, and auto-updating RR directly on your Discord profile game card!

### 🎯 Dynamic Match Simulation Engine:
- **Skor Dinamis Realistis**: Ronde berjalan bertahap dari `0-0`, `1-0`, `1-1`, hingga `13` poin (termasuk skenario overtime `14-12`).
- **Siklus Hidup Match Otomatis**: `In Match` ➔ `Victory / Defeat Screen` ➔ `In Lobby (In Queue)` ➔ `Agent Select` ➔ `Next Match`.
- **Filter Map Kompetitif Aktif**: Hanya memilih dari **7 map aktif Ranked** (`Ascent`, `Bind`, `Haven`, `Lotus`, `Sunset`, `Abyss`), menghindari map yang sedang di-patch/keluar dari rotasi.
- **Auto RR Progression**: RR bertambah dinamis saat menang (+18 hingga +24 RR) dan berkurang wajar saat kalah.
- **Mobile-Clean**: Teks ringkas (Baris 1: `Radiant (845 RR)`, Baris 2: `Ascent (7-5) (5 of 5)`), pas di box Discord HP tanpa terpotong!

### Quick Start:
```bash
# 1. Mode Realistis (Ronde bertambah ~90 detik, match ~30 menit, persis seperti main asli):
py valorant_rpc.py

# 2. Mode Realistis Langsung Mulai Pertengahan Match (Skor ~5-3):
py valorant_rpc.py --start-mid

# 3. Mode Cepat / Demo Testing (Skor bertambah tiap 8-10 detik untuk demonstrasi cepat):
py valorant_rpc.py --fast

# Kunci Agent Tertentu (opsional):
py valorant_rpc.py --agent Jett
```

---

## 🏆 Official Discord Badge Tier Reference

Data hierarchy verified directly from Discord's client UI:

### 🗡️ Game Time Badges (`rdiscord.py`)
> *Tracked by accumulating hours in detectable PC games with Discord open.*

| Required Playtime | Badge Title | Visual Tier / Color |
|---:|:---|:---|
| **1 Hour** | **Casual** | ⚪ Grey Sword |
| **5 Hours** | **Recreational** | 🟢 Light Green Sword |
| **20 Hours** | **Dedicated** | 🟢 Green Sword |
| **75 Hours** | **Committed** | 🔵 Cyan Sword |
| **150 Hours** | **Serious** | 🟦 Teal Sword |
| **300 Hours** | **Devoted** | 🟦 Blue Sword |
| **500 Hours** | **Seasoned** | 🟣 Purple Sword (Rare) |
| **1,000 Hours** | **Ironclad** | 🟣 Magenta Sword |
| **2,000 Hours** | **Unshakeable** | 🔴 Red Sword |
| **5,000+ Hours** | **Eternal** | 🟡 Gold Sword |

### 🎮 Game Variety Badges (`rdiscord.py`)
> *Tracked by launching multiple unique detectable PC games.*

| Unique Games Played | Badge Title | Visual Tier / Color |
|---:|:---|:---|
| **2 Games** | **Sampler** | ⚪ Grey Controller |
| **5 Games** | **Dabbler** | 🟢 Light Green Controller |
| **10 Games** | **Enthusiast** | 🟢 Green Controller |
| **15 Games** | **Ranger** | 🔵 Cyan Controller |
| **20 Games** | **Explorer** | 🟦 Teal Controller |
| **30 Games** | **Adventurer** | 🟦 Blue Controller |
| **40 Games** | **Voyager** | 🟣 Purple Controller |
| **60 Games** | **Maverick** | 🟣 Magenta Controller |
| **80 Games** | **Polymath** | 🔴 Red Controller |
| **100+ Games** | **Universalist** | 🟡 Gold Controller |

### 🖥️ Streaming Badges (`rstream.py`)
> *Tracked by streaming (Go Live) to other users in voice channels.*

| Required Stream Hours | Badge Title | Visual Tier / Color |
|---:|:---|:---|
| **1 Hour** | **Newcomer** | ⚪ Grey Monitor |
| **5 Hours** | **Fledgling** | 🟢 Light Green Monitor |
| **20 Hours** | **Breakout** | 🟢 Green Monitor |
| **75 Hours** | **Standout** | 🔵 Cyan Monitor |
| **150 Hours** | **Trendsetter** | 🟦 Teal Monitor |
| **300 Hours** | **Headliner** | 🟦 Blue Monitor |
| **500 Hours** | **Star** | 🟣 Purple Monitor |
| **1,000 Hours** | **Sensation** | 🟣 Magenta Monitor |
| **2,000 Hours** | **Visionary** | 🔴 Red Monitor |
| **5,000+ Hours** | **Phenomenon** | 🟡 Gold Monitor |

---

## 🔑 Extracting Your Credentials

<details>
<summary><b>▶ Click to view instructions: Discord Token</b></summary>

1. Open [Discord Web](https://discord.com/app) in your Chromium browser and log in.
2. Press **`F12`** to open Developer Tools.
3. Switch to the **Console** tab.
4. If prompted, type `allow pasting` and press Enter.
5. Execute the following snippet:
   ```javascript
   (webpackChunkdiscord_app.push([[''],{},e=>{m=[];for(let c in e.c)m.push(e.c[c])}]),m).find(m=>m?.exports?.default?.getToken!==void 0).exports.default.getToken()
   ```
6. Copy the output string (without quotes).
</details>

<details>
<summary><b>▶ Click to view instructions: Cloudflare cf_clearance</b></summary>

1. In DevTools, navigate to the **Application** tab (Chrome/Edge) or **Storage** (Firefox).
2. Go to **Cookies** ➔ `https://discord.com`.
3. Locate the row named **`cf_clearance`**.
4. Copy its **Value**.
5. Paste it when prompted by the script as: `cf_clearance=<value>`.
</details>

---

## 📁 Repository Structure

```
discord-badge-spoofer/
├── rdiscord.py          # Primary game playtime & game variety telemetry spoofer
├── rstream.py           # Go Live voice/stream session telemetry spoofer
├── hypesquad.js         # Instant DevTools console script for HypeSquad badge
├── valorant_rpc.py      # VALORANT Radiant rank & live match Discord RPC card
├── science_state.json   # DPAPI-encrypted credential store & telemetry cache
├── .gitignore           # Git ignore rules for clean repository hygiene
├── LICENSE              # MIT Open Source License
└── README.md            # Comprehensive project documentation
```

---

## ⚠️ Responsible Disclosure & Disclaimer

> [!WARNING]
> This software interacts with private, internal Discord endpoints (`/api/v9/science`).
> Using automated scripts on user accounts violates the [Discord Terms of Service](https://discord.com/terms).
> The authors accept **no liability** for account penalties, restrictions, or terminations.
>
> **This project was developed strictly as an educational study on client-side telemetry architectures, reverse engineering, and Windows DPAPI credential hardening.**

---

## 📄 License

Distributed under the **MIT License**. See [`LICENSE`](LICENSE) for complete details.

```
Copyright (c) 2026 SahrulRD-Smatel
```

<p align="center">
  <sub>Engineered with precision by <a href="https://github.com/SahrulRD-Smatel"><b>SahrulRD-Smatel</b></a></sub>
</p>
