# 🌐 User-Agent List (Automated & Curated)

[![Python 3.8+](https://img.shields.io/badge/Python-3.8+-3776AB?style=flat-square&logo=python&logoColor=white)](https://www.python.org/)
[![Auto Update](https://img.shields.io/badge/Auto--Update-Daily%20(GitHub%20Actions)-10B981?style=flat-square&logo=github-actions&logoColor=white)](#)
[![License: Apache 2.0](https://img.shields.io/badge/License-Apache%202.0-blue?style=flat-square)](LICENSE)
[![Status: Maintained](https://img.shields.io/badge/Status-Maintained-3D5AFE?style=flat-square)](#)

Kumpulan daftar **User-Agent (UA) string** terkini dan terverifikasi untuk berbagai peramban desktop, perangkat mobile, sistem operasi, serta in-app browser media sosial.

**`ua.txt`** (browser umum — Chrome, Firefox, Safari, Edge, desktop & mobile) diperbarui **otomatis setiap hari** via GitHub Actions menggunakan `scraper.py` yang mengambil data langsung dari [useragents.me](https://www.useragents.me/).

File UA **app-specific** (Facebook, Instagram, Twitter/X, UC Browser) dikelola **secara manual** karena tidak ada API publik yang reliabel untuk data tersebut — dan mungkin tidak selalu yang paling mutakhir.

File kategorikal di `data/` (browsers, chrome, firefox, dll.) diperbarui terpisah via `fetch_user_agents.py` yang berjalan mingguan.

---

## 📑 Daftar Isi

- [Struktur Folder](#-struktur-folder)
- [Kategori User-Agent yang Tersedia](#-kategori-user-agent-yang-tersedia)
- [Sumber Data & API](#-sumber-data--api)
- [Cara Menggunakan User-Agent](#-cara-menggunakan-user-agent)
  - [1. Python Requests (Rotasi Acak)](#1-python-requests-rotasi-acak)
  - [2. cURL Terminal](#2-curl-terminal)
  - [3. Playwright / Puppeteer (Node.js)](#3-playwright--puppeteer-nodejs)
- [Cara Menjalankan Script Otomasi](#-cara-menjalankan-script-otomasi)
  - [Manual via Terminal](#manual-via-terminal)
  - [Konfigurasi .env (Opsional)](#konfigurasi-env-opsional)
- [Otomasi Terjadwal (GitHub Actions)](#-otomasi-terjadwal-github-actions)
- [Lisensi](#-lisensi)

---

## 📁 Struktur Folder

```text
user-agent-list/
├── fetch_user_agents.py         # Script utama pengambil & pengkategori User-Agent
├── data/                        # Folder kumpulan file User-Agent (.txt)
│   ├── browsers.txt             # Desktop & general web browsers
│   ├── mobile.txt               # Mobile browsers (Android & iOS)
│   ├── chrome.txt               # Google Chrome
│   ├── firefox.txt              # Mozilla Firefox
│   ├── safari.txt               # Apple Safari
│   ├── edge.txt                 # Microsoft Edge
│   ├── windows.txt              # OS Windows
│   ├── macos.txt                # macOS
│   ├── android.txt              # Android OS
│   ├── ios.txt                  # Apple iOS (iPhone/iPad)
│   ├── social.txt               # In-App browser (Instagram, Facebook, Twitter/X)
│   └── uc-browser.txt           # UC Browser
├── .github/
│   └── workflows/
│       └── update-user-agents.yml # Auto-update mingguan via GitHub Actions
├── requirements.txt             # Dependensi Python
├── .env.example                 # Contoh template konfigurasi API
├── .gitignore                   # Ignore cache dan file sensitif
├── LICENSE                      # Lisensi resmi Apache 2.0
└── README.md                    # Dokumentasi lengkap
```

Setiap file di dalam folder `data/` memiliki format **satu User-Agent per baris**, siap dibaca (*streamed*) baris demi baris oleh script scraping atau automation tool Anda.

---

## 📊 Kategori User-Agent yang Tersedia

| File Output | Kategori / Target | Deskripsi |
| :--- | :--- | :--- |
| **`data/browsers.txt`** | Desktop & Web Browsers | Kumpulan browser desktop paling populer di internet |
| **`data/mobile.txt`** | Mobile Browsers | Browser mobile Android, iPhone, dan iPad |
| **`data/chrome.txt`** | Google Chrome | Varian User-Agent Chrome (Windows, Mac, Linux) |
| **`data/firefox.txt`** | Mozilla Firefox | Varian User-Agent Firefox (Gecko engine) |
| **`data/safari.txt`** | Apple Safari | Varian User-Agent WebKit murni Safari macOS & iOS |
| **`data/edge.txt`** | Microsoft Edge | Varian User-Agent Chromium Edge terbaru |
| **`data/windows.txt`** | Windows OS | Peramban yang berjalan di Windows 10/11 |
| **`data/macos.txt`** | macOS | Peramban yang berjalan di Apple macOS Intel/Apple Silicon |
| **`data/android.txt`** | Android | Perangkat ponsel & tablet Android |
| **`data/ios.txt`** | Apple iOS | iPhone, iPad, dan iPod Touch |
| **`data/social.txt`** | In-App Social Media | Browser internal Facebook, Instagram, Twitter/X, TikTok |
| **`data/uc-browser.txt`**| UC Browser | Koleksi peramban seluler UC Browser |

---

## 🔌 Sumber Data & API

Script `fetch_user_agents.py` mengambil data dari beberapa sumber terpercaya untuk memastikan daftar selalu *up-to-date*:

1. **Microlink Top User-Agents Telemetry**: Data distribusi real-time browser desktop dan mobile global.
2. **Jnrbsn Live User-Agents Feed**: Koleksi rilis versi peramban modern yang diperbarui secara reguler.
3. **Curated Browser Datasets**: Feed terfilter untuk Chrome, Firefox, Safari, Edge, dan Opera.
4. **WhatIsMyBrowser API (Opsional)**: Mendukung integrasi dengan WhatIsMyBrowser API jika Anda memasukkan `WHATISMYBROWSER_API_KEY` di file `.env`.
5. **Historical Social & Mobile Archive**: Data in-app browser media sosial (Facebook, Instagram, Twitter) yang telah di-deduplikasi dan dibersihkan dari versi sebelumnya.

---

## 💡 Cara Menggunakan User-Agent

### 1. Python Requests (Rotasi Acak)
Cocok untuk web scraping guna menghindari deteksi bot dan pemblokiran IP:

```python
import random
import requests

def get_random_user_agent(category="browsers"):
    file_path = f"data/{category}.txt"
    with open(file_path, "r", encoding="utf-8") as f:
        user_agents = [line.strip() for line in f if line.strip()]
    return random.choice(user_agents)

# Contoh request dengan User-Agent acak
headers = {
    "User-Agent": get_random_user_agent("chrome")
}
response = requests.get("https://httpbin.org/user-agent", headers=headers)
print(response.json())
```

### 2. cURL Terminal
Menguji respon server menggunakan mobile atau desktop UA:

```bash
# Mengambil satu UA mobile dan melakukan request
UA=$(shuf -n 1 data/mobile.txt)
curl -H "User-Agent: $UA" https://example.com
```

### 3. Playwright / Puppeteer (Node.js)
```javascript
const { chromium } = require('playwright');
const fs = require('fs');

const userAgents = fs.readFileSync('data/browsers.txt', 'utf-8').split('\n').filter(Boolean);
const randomUA = userAgents[Math.floor(Math.random() * userAgents.length)];

(async () => {
  const browser = await chromium.launch();
  const context = await browser.newContext({ userAgent: randomUA });
  const page = await context.newPage();
  await page.goto('https://httpbin.org/user-agent');
  console.log(await page.content());
  await browser.close();
})();
```

---

## 🚀 Cara Menjalankan Script Otomasi

### Manual via Terminal

1. **Kloning Repository & Masuk ke Folder**:
   ```bash
   git clone https://github.com/SoraDev-ID/user-agent-list.git
   cd user-agent-list
   ```

2. **Pasang Dependensi**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Jalankan Script Fetcher**:
   ```bash
   python fetch_user_agents.py
   ```
   *Script akan otomatis mengambil data terbaru, melakukan deduplikasi, dan memperbarui seluruh file di dalam folder `data/`.*

### Konfigurasi `.env` (Opsional)
Jika Anda memiliki lisensi/API Key WhatIsMyBrowser:
```bash
cp .env.example .env
```
Lalu edit file `.env`:
```env
WHATISMYBROWSER_API_KEY=masukkan_api_key_anda
```

---

## ⏰ Otomasi Terjadwal (GitHub Actions)

Repository ini memiliki **dua workflow otomasi** yang berjalan secara independen:

### 1. 🤖 `ua.txt` — Update Harian (Browser Umum)

File `.github/workflows/update-ua.yml` menjalankan `scraper.py` setiap hari pukul **03:00 UTC**.

- **Sumber data**: [useragents.me](https://www.useragents.me/) — endpoint `desktop` + `mobile`
- **Output**: `ua.txt` (satu UA per baris, dedupe, sorted) + `last_updated.txt` (JSON + summary)
- **Retry**: 3x dengan backoff eksponensial; jika semua sumber gagal → exit non-zero, workflow gagal, file tidak ditimpa
- **Commit**: Hanya jika `ua.txt` atau `last_updated.txt` berubah (`git diff --staged --quiet`)
- **Manual trigger**: Tab **Actions** → **Daily User-Agent Auto-Update (ua.txt)** → **Run workflow**

**File yang TIDAK disentuh workflow ini** (tetap dikelola manual):

| File | Keterangan |
| :--- | :--- |
| `uaFacebook.txt`, `uafb.txt` | UA Facebook App — tidak ada API publik reliabel |
| `uame.txt` | UA khusus — dikelola manual |
| `user-agents_instagram-app_application_android.txt` | UA Instagram App |
| `user-agents_twitter-app_application.txt` | UA Twitter/X App |
| `user-agents_uc-browser_browser_13-3.txt` | UA UC Browser versi spesifik |
| `ua.zip` | Arsip lama — tidak pernah digenerate ulang |

### 2. 📂 `data/` — Update Mingguan (Semua Kategori)

File `.github/workflows/update-user-agents.yml` menjalankan `fetch_user_agents.py` setiap **Minggu pukul 00:00 UTC**, memperbarui seluruh file di folder `data/` (browsers, chrome, firefox, safari, edge, mobile, dll.).



---

## 📄 Lisensi

Didistribusikan di bawah lisensi resmi **Apache License 2.0**. Bebas digunakan untuk keperluan riset, pengujian kompabilitas, web crawling, dan pengembangan aplikasi. Lihat file [LICENSE](LICENSE) untuk informasi lebih lanjut.

---

<p align="center">
  Dikelola oleh <b><a href="https://github.com/SoraDev-ID">SoraDev-ID</a></b>
</p>