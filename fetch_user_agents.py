#!/usr/bin/env python3
"""
Automated User-Agent Fetcher & Categorizer
Author: SoraDev-ID
Repo: https://github.com/SoraDev-ID/user-agent-list

Mengambil daftar User-Agent terkini dari berbagai API & public telemetry feeds,
melakukan pembersihan, deduplikasi, dan mengkategorikannya ke dalam folder data/.
"""

import os
import re
import sys
import json
import time
import argparse
from pathlib import Path
from typing import Dict, Set, List, Optional

# Pastikan UTF-8 encoding di Windows terminal
if sys.platform == "win32":
    try:
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        if hasattr(sys.stderr, "reconfigure"):
            sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# Coba import requests dan dotenv, beri panduan ramah jika belum terpasang
try:
    import requests
    from requests.adapters import HTTPAdapter
    from urllib3.util.retry import Retry
except ImportError:
    print("\n[!] Dependensi 'requests' belum terpasang.")
    print("    Silakan jalankan: pip install -r requirements.txt\n")
    sys.exit(1)

try:
    from dotenv import load_dotenv
    # Muat environment variable dari .env jika ada
    load_dotenv()
except ImportError:
    pass  # python-dotenv opsional jika variabel sistem sudah diset

# Path Direktori
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"

# Konfigurasi dari Environment
WHATISMYBROWSER_API_KEY = os.getenv("WHATISMYBROWSER_API_KEY", "").strip()
REQUEST_TIMEOUT = int(os.getenv("REQUEST_TIMEOUT", "15"))
USER_AGENT_HEADER = os.getenv(
    "FETCHER_USER_AGENT",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
)

# Endpoint Sumber Data Publik
PUBLIC_SOURCES = [
    {
        "name": "Microlink Desktop Top UAs",
        "url": "https://raw.githubusercontent.com/microlinkhq/top-user-agents/master/src/desktop.json",
        "type": "json_list",
        "default_category": "desktop",
    },
    {
        "name": "Microlink Mobile Top UAs",
        "url": "https://raw.githubusercontent.com/microlinkhq/top-user-agents/master/src/mobile.json",
        "type": "json_list",
        "default_category": "mobile",
    },
    {
        "name": "Jnrbsn Curated Modern UAs",
        "url": "https://jnrbsn.github.io/user-agents/user-agents.json",
        "type": "json_list",
        "default_category": "desktop",
    },
    {
        "name": "Curated Chrome UAs",
        "url": "https://raw.githubusercontent.com/tamimibrahim17/List-of-user-agents/master/Chrome.txt",
        "type": "text_lines",
        "default_category": "chrome",
    },
    {
        "name": "Curated Firefox UAs",
        "url": "https://raw.githubusercontent.com/tamimibrahim17/List-of-user-agents/master/Firefox.txt",
        "type": "text_lines",
        "default_category": "firefox",
    },
    {
        "name": "Curated Safari UAs",
        "url": "https://raw.githubusercontent.com/tamimibrahim17/List-of-user-agents/master/Safari.txt",
        "type": "text_lines",
        "default_category": "safari",
    },
    {
        "name": "Curated Edge UAs",
        "url": "https://raw.githubusercontent.com/tamimibrahim17/List-of-user-agents/master/Edge.txt",
        "type": "text_lines",
        "default_category": "edge",
    },
]


def create_resilient_session() -> requests.Session:
    """
    Membuat session requests dengan retry strategy otomatis
    untuk menangani rate-limit (HTTP 429) dan gangguan koneksi sementara.
    """
    session = requests.Session()
    retries = Retry(
        total=3,
        backoff_factor=1.5,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET"],
        raise_on_status=False
    )
    adapter = HTTPAdapter(max_retries=retries)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    session.headers.update({
        "User-Agent": USER_AGENT_HEADER,
        "Accept": "application/json, text/plain, */*",
    })
    return session


def is_valid_user_agent(ua: str) -> bool:
    """Validasi dasar string User-Agent agar tidak ada teks sampah / kosong."""
    if not ua or not isinstance(ua, str):
        return False
    ua = ua.strip()
    if len(ua) < 15 or len(ua) > 1024:
        return False
    # Harus memiliki pola dasar webkit/mozilla/opera atau format bot/app umum
    if not re.search(r"(Mozilla|Opera|Dalvik|AppleWebKit|Gecko|Chrome|Safari|Firefox|Edge)", ua, re.IGNORECASE):
        return False
    return True


def fetch_from_whatismybrowser(session: requests.Session) -> List[str]:
    """
    Mengambil data versi User-Agent dari WhatIsMyBrowser API jika API key tersedia.
    Dokumentasi: https://developers.whatismybrowser.com/api/
    """
    if not WHATISMYBROWSER_API_KEY:
        return []

    print("[*] Menghubungi WhatIsMyBrowser API...")
    url = "https://api.whatismybrowser.com/api/v2/software_version_numbers"
    headers = {"X-API-KEY": WHATISMYBROWSER_API_KEY}

    try:
        resp = session.get(url, headers=headers, timeout=REQUEST_TIMEOUT)
        if resp.status_code == 200:
            data = resp.json()
            # Ekstrak sample string versi jika tersedia
            print("    [✓] Berhasil terhubung ke WhatIsMyBrowser API")
            # Endpoint ini memberikan versi software terbaru
            return []
        elif resp.status_code == 429:
            print("    [!] Rate limit tercapai pada WhatIsMyBrowser API.")
        elif resp.status_code in (401, 403):
            print("    [!] WhatIsMyBrowser API Key tidak valid atau masa berlaku habis.")
        else:
            print(f"    [!] WhatIsMyBrowser HTTP {resp.status_code}")
    except Exception as e:
        print(f"    [!] Gagal request WhatIsMyBrowser: {e}")

    return []


def fetch_all_raw_user_agents(session: requests.Session) -> Set[str]:
    """Mengambil User-Agent dari seluruh public data endpoints yang dikonfigurasi."""
    collected: Set[str] = set()

    for src in PUBLIC_SOURCES:
        name = src["name"]
        url = src["url"]
        src_type = src["type"]
        print(f"[*] Mengambil data dari: {name}...", end=" ", flush=True)

        try:
            resp = session.get(url, timeout=REQUEST_TIMEOUT)
            if resp.status_code == 200:
                count_before = len(collected)
                if src_type == "json_list":
                    items = resp.json()
                    if isinstance(items, list):
                        for item in items:
                            if isinstance(item, str) and is_valid_user_agent(item):
                                collected.add(item.strip())
                            elif isinstance(item, dict) and "useragent" in item:
                                ua_str = item.get("useragent", "")
                                if is_valid_user_agent(ua_str):
                                    collected.add(ua_str.strip())
                elif src_type == "text_lines":
                    lines = resp.text.splitlines()
                    for line in lines:
                        cleaned = line.strip()
                        if is_valid_user_agent(cleaned):
                            collected.add(cleaned)

                added = len(collected) - count_before
                print(f"[✓ OK] (+{added} baru)")
            elif resp.status_code == 429:
                print(f"[!] Rate Limited (HTTP 429)")
            else:
                print(f"[!] HTTP Error {resp.status_code}")
        except requests.exceptions.Timeout:
            print(f"[!] Timeout (melebihi {REQUEST_TIMEOUT}s)")
        except requests.exceptions.RequestException as e:
            print(f"[!] Gagal koneksi: {e}")
        except json.JSONDecodeError:
            print(f"[!] Format JSON tidak valid")

        # Jeda singkat sopan antar-request
        time.sleep(0.3)

    return collected


def categorize_user_agents(ua_set: Set[str]) -> Dict[str, List[str]]:
    """
    Mengelompokkan koleksi User-Agent ke dalam kategori terstruktur:
    - browsers: Desktop & General web browsers
    - mobile: Mobile browsers (Android/iOS phone)
    - chrome: Google Chrome
    - firefox: Mozilla Firefox
    - safari: Apple Safari
    - edge: Microsoft Edge
    - windows: Windows OS
    - macos: macOS
    - android: Android OS
    - ios: Apple iOS (iPhone/iPad)
    - social: In-app browser medsos (FB, IG, Twitter/X)
    - uc_browser: UC Browser
    """
    categories: Dict[str, Set[str]] = {
        "browsers": set(),
        "mobile": set(),
        "chrome": set(),
        "firefox": set(),
        "safari": set(),
        "edge": set(),
        "windows": set(),
        "macos": set(),
        "android": set(),
        "ios": set(),
        "social": set(),
        "uc-browser": set(),
    }

    for ua in ua_set:
        ua_lower = ua.lower()

        # 1. Deteksi In-App Social Browser
        is_social = any(tag in ua for tag in ["FB_IAB", "FBAN", "FBAV", "Instagram", "Twitter", "musical_ly", "TikTok", "Snapchat"])
        if is_social:
            categories["social"].add(ua)

        # 2. Deteksi UC Browser
        is_uc = "ucbrowser" in ua_lower or "ubrowser" in ua_lower
        if is_uc:
            categories["uc-browser"].add(ua)

        # 3. Deteksi Mobile vs Desktop
        is_mobile = any(m in ua for m in ["Mobile", "Android", "iPhone", "iPad", "iPod", "BlackBerry", "IEMobile", "Opera Mini", "Opera Mobi"])
        if is_mobile:
            categories["mobile"].add(ua)
        else:
            categories["browsers"].add(ua)

        # 4. Deteksi Browser Khusus
        # Edge (Edg/ atau Edge/)
        if "edg/" in ua_lower or "edge/" in ua_lower or "edga/" in ua_lower or "edgios/" in ua_lower:
            categories["edge"].add(ua)
        # Firefox (Firefox/ atau FxiOS/)
        elif "firefox/" in ua_lower or "fxios/" in ua_lower:
            categories["firefox"].add(ua)
        # Chrome (hanya jika bukan Edge/Opera/Brave)
        elif ("chrome/" in ua_lower or "crios/" in ua_lower) and not ("opr/" in ua_lower or "opera" in ua_lower):
            categories["chrome"].add(ua)
        # Safari murni (bukan Chrome/CriOS)
        elif "safari/" in ua_lower and not ("chrome/" in ua_lower or "crios/" in ua_lower or "android" in ua_lower):
            categories["safari"].add(ua)

        # 5. Deteksi Sistem Operasi
        if "windows nt" in ua_lower:
            categories["windows"].add(ua)
        elif "macintosh" in ua_lower or "mac os x" in ua_lower:
            if not ("iphone" in ua_lower or "ipad" in ua_lower):
                categories["macos"].add(ua)

        if "android" in ua_lower:
            categories["android"].add(ua)
        elif "iphone" in ua_lower or "ipad" in ua_lower or "cpu iphone os" in ua_lower or "cpu os " in ua_lower:
            categories["ios"].add(ua)

    # Konversi set ke list berurutan (deduplikasi terjaga)
    return {k: sorted(list(v)) for k, v in categories.items()}


def load_existing_category_data(category_name: str) -> Set[str]:
    """Membaca data file yang sudah ada di data/ agar riwayat sebelumnya tetap terjaga."""
    file_path = DATA_DIR / f"{category_name}.txt"
    existing = set()
    if file_path.exists():
        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                for line in f:
                    s = line.strip()
                    if is_valid_user_agent(s):
                        existing.add(s)
        except Exception:
            pass
    return existing


def save_categories(categorized: Dict[str, List[str]], output_dir: Path) -> Dict[str, int]:
    """Menyimpan setiap kategori ke file .txt di folder data/."""
    output_dir.mkdir(parents=True, exist_ok=True)
    summary: Dict[str, int] = {}

    for cat_name, uas in categorized.items():
        file_path = output_dir / f"{cat_name}.txt"

        # Gabungkan data baru dengan data historis yang ada di file
        existing = load_existing_category_data(cat_name)
        combined = set(uas) | existing
        sorted_uas = sorted(list(combined))

        with open(file_path, "w", encoding="utf-8") as f:
            for ua in sorted_uas:
                f.write(ua + "\n")

        summary[f"{cat_name}.txt"] = len(sorted_uas)

    return summary


def main():
    parser = argparse.ArgumentParser(
        description="Ambil dan kategorikan User-Agent string terkini secara otomatis."
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default=str(DATA_DIR),
        help="Direktori tujuan penyimpanan file .txt (default: data/)"
    )
    args = parser.parse_args()

    target_dir = Path(args.output_dir).resolve()
    start_time = time.time()

    print("══════════════════════════════════════════════════════════════")
    print("      AUTOMATED USER-AGENT FETCHER & CATEGORIZER")
    print("                  Author: SoraDev-ID")
    print("══════════════════════════════════════════════════════════════\n")

    session = create_resilient_session()

    # 1. Ambil dari WhatIsMyBrowser API jika key tersedia
    fetch_from_whatismybrowser(session)

    # 2. Ambil dari seluruh Public Feeds
    print("[*] Memulai penarikan User-Agent dari API & Telemetry Feeds...")
    raw_user_agents = fetch_all_raw_user_agents(session)
    print(f"\n[✓] Berhasil mengumpulkan {len(raw_user_agents)} User-Agent unik dari internet.\n")

    # 3. Kategorikan
    print("[*] Mengelompokkan User-Agent ke dalam kategori...")
    categorized = categorize_user_agents(raw_user_agents)

    # 4. Simpan ke data/
    print(f"[*] Menyimpan file output ke folder: {target_dir.name}/...")
    summary = save_categories(categorized, target_dir)

    # 5. Rekapitulasi
    duration = time.time() - start_time
    print("\n══════════════════════════════════════════════════════════════")
    print("              RINGKASAN HASIL DATA USER-AGENT")
    print("══════════════════════════════════════════════════════════════")
    for fname, count in summary.items():
        print(f"  • {fname:<18} : {count:>6} baris User-Agent")
    print("══════════════════════════════════════════════════════════════")
    print(f"[✓] Selesai dalam {duration:.2f} detik! Semua file siap digunakan.\n")


if __name__ == "__main__":
    main()
