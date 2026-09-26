#!/usr/bin/env python3
"""
ua.txt Auto-Updater -- useragents.me HTML scraper
Author  : SoraDev-ID
Repo    : https://github.com/SoraDev-ID/user-agent-list

Mengambil daftar User-Agent browser umum terkini dari useragents.me
dengan mem-parse JSON yang di-embed dalam halaman HTML (textarea).
Menggabungkan UA desktop + mobile, mendedupe, dan menulis ke ua.txt
(satu UA per baris, plain text, tanpa metadata).

Juga menghasilkan / memperbarui last_updated.txt berisi timestamp UTC &
WIB, jumlah UA, dan status run -- format JSON machine-parseable +
human-readable summary.

Usage
-----
  python scraper.py                  # fetch & tulis ua.txt + last_updated.txt
  python scraper.py --dry-run        # fetch & cetak ke stdout, TIDAK tulis file
  python scraper.py --timeout 15     # ubah request timeout (default: 10 detik)
  python scraper.py --retries 3      # ubah jumlah retry (default: 3)

Exit codes
----------
  0  -- sukses
  1  -- seluruh sumber gagal (network error / down) -> tidak ada UA yang di-fetch
"""

import re
import sys
import json
import time
import argparse
from pathlib import Path
from datetime import datetime, timezone, timedelta

# -- Windows UTF-8 safety
if sys.platform == "win32":
    try:
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        if hasattr(sys.stderr, "reconfigure"):
            sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

try:
    import requests
    from requests.adapters import HTTPAdapter
    from urllib3.util.retry import Retry
except ImportError:
    print("[!] Dependensi 'requests' belum terpasang.")
    print("    Jalankan: pip install -r requirements.txt")
    sys.exit(1)

# ============================================================
# Konstanta
# ============================================================
BASE_DIR = Path(__file__).resolve().parent

# useragents.me embed data JSON di textarea halaman HTML.
# Kedua section: most-common-desktop-useragents-json-csv &
#                most-common-mobile-useragents-json-csv
# Pattern textarea yang memuat JSON array of {"ua":..., "pct":...}
UA_SOURCES = {
    "desktop": {
        "url":      "https://www.useragents.me/",
        "anchor_id": "most-common-desktop-useragents-json-csv",
        "label":     "Desktop (useragents.me)",
    },
    "mobile": {
        "url":      "https://www.useragents.me/",
        "anchor_id": "most-common-mobile-useragents-json-csv",
        "label":     "Mobile (useragents.me)",
    },
}

OUTPUT_FILE       = BASE_DIR / "ua.txt"
LAST_UPDATED_FILE = BASE_DIR / "last_updated.txt"

FETCH_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/128.0.0.0 Safari/537.36"
)

# Regex: cari blok <div id="...-json-csv"...> lalu ambil konten textarea pertama di dalamnya
# Textarea berisi JSON array langsung tanpa escaping tambahan.
_SECTION_PATTERN = re.compile(
    r'<div\s[^>]*id=["\'](?P<id>[^"\']+)["\'][^>]*>.*?</div>',
    re.DOTALL,
)
_TEXTAREA_JSON_PATTERN = re.compile(
    r'<textarea[^>]*>\s*(\[.*?\])\s*</textarea>',
    re.DOTALL,
)


# ============================================================
# Session factory
# ============================================================

def create_session(timeout: int, retries: int) -> "requests.Session":
    session = requests.Session()
    retry_cfg = Retry(
        total=retries,
        backoff_factor=1.5,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET"],
        raise_on_status=False,
    )
    adapter = HTTPAdapter(max_retries=retry_cfg)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    session.headers.update({
        "User-Agent": FETCH_USER_AGENT,
        "Accept": "text/html,application/xhtml+xml,*/*",
    })
    session._custom_timeout = timeout
    return session


# ============================================================
# Fetch & parse
# ============================================================

def _extract_uas_from_section(html: str, anchor_id: str) -> list:
    """
    Temukan section <div id="{anchor_id}-json-csv"...> di HTML,
    lalu parse JSON dari textarea pertama di dalamnya.
    Return list UA string, atau list kosong jika gagal.
    """
    # Cari posisi anchor id dalam HTML
    marker = f'id="{anchor_id}"'
    if marker not in html:
        marker = f"id='{anchor_id}'"
    pos = html.find(marker)
    if pos == -1:
        return []

    # Ambil potongan HTML dari anchor ke depan (maksimal 8000 karakter)
    snippet = html[pos: pos + 8000]

    # Cari textarea yang memuat JSON array
    m = _TEXTAREA_JSON_PATTERN.search(snippet)
    if not m:
        return []

    raw_json = m.group(1)
    try:
        items = json.loads(raw_json)
    except (json.JSONDecodeError, ValueError):
        return []

    uas = []
    for item in items:
        if isinstance(item, dict):
            ua = item.get("ua", "").strip()
        elif isinstance(item, str):
            ua = item.strip()
        else:
            continue
        if ua:
            uas.append(ua)
    return uas


def fetch_page_html(session: "requests.Session", url: str, label: str) -> str:
    """Fetch halaman HTML; return string kosong jika gagal."""
    timeout = getattr(session, "_custom_timeout", 10)
    print(f"[*] Menghubungi {url} ...", end=" ", flush=True)
    try:
        resp = session.get(url, timeout=timeout)
        if resp.status_code == 200:
            print("[OK]")
            return resp.text
        print(f"[!] HTTP {resp.status_code}")
        return ""
    except requests.exceptions.Timeout:
        print(f"[!] Timeout setelah {timeout}s")
        return ""
    except requests.exceptions.ConnectionError as exc:
        print(f"[!] Koneksi gagal: {exc}")
        return ""
    except requests.exceptions.RequestException as exc:
        print(f"[!] Request error: {exc}")
        return ""


def fetch_all_ua(session: "requests.Session") -> tuple:
    """
    Fetch halaman useragents.me sekali, lalu parse section desktop & mobile.
    Return (list_ua, list_failed_labels).
    """
    html = fetch_page_html(session, "https://www.useragents.me/", "useragents.me")
    if not html:
        return [], ["desktop", "mobile"]

    all_uas = []
    failed = []
    for key, cfg in UA_SOURCES.items():
        anchor = cfg["anchor_id"]
        label  = cfg["label"]
        print(f"[*] Parsing section '{key}' (anchor: {anchor}) ...", end=" ", flush=True)
        uas = _extract_uas_from_section(html, anchor)
        if uas:
            print(f"[OK] {len(uas)} UA ditemukan.")
            all_uas.extend(uas)
        else:
            print(f"[!] Tidak ada UA ditemukan -- dilewati.")
            failed.append(key)

    return all_uas, failed


# ============================================================
# File I/O
# ============================================================

def write_ua_file(uas: list, path: "Path") -> int:
    unique_sorted = sorted(set(uas))
    with open(path, "w", encoding="utf-8") as f:
        for ua in unique_sorted:
            f.write(ua + "\n")
    return len(unique_sorted)


def write_last_updated(count: int, duration: float, status: str, path: "Path") -> None:
    now_utc = datetime.now(timezone.utc)
    wib_tz  = timezone(timedelta(hours=7))
    now_wib = now_utc.astimezone(wib_tz)
    json_data = {
        "updated_at_utc":   now_utc.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "updated_at_wib":   now_wib.strftime("%Y-%m-%dT%H:%M:%S+07:00"),
        "duration_seconds": round(duration, 2),
        "ua_count":         count,
        "source":           "useragents.me (desktop + mobile)",
        "status":           status,
    }
    str_utc = now_utc.strftime("%Y-%m-%d %H:%M:%S UTC")
    str_wib = now_wib.strftime("%Y-%m-%d %H:%M:%S WIB")
    content = (
        "### MACHINE-PARSEABLE JSON ###\n"
        + json.dumps(json_data, indent=2)
        + "\n\n"
        "### HUMAN-READABLE SUMMARY ###\n"
        "================================================================\n"
        "        User-Agent List -- Status Pembaruan Terakhir\n"
        "================================================================\n"
        f"Waktu Update (UTC) : {str_utc}\n"
        f"Waktu Update (WIB) : {str_wib}\n"
        f"Durasi             : {duration:.2f} detik\n"
        "================================================================\n"
        f"Sumber             : useragents.me (desktop + mobile)\n"
        f"Total UA di ua.txt : {count:>6} entri\n"
        f"Status             : {status}\n"
        "================================================================\n"
    )
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)


# ============================================================
# Main
# ============================================================

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Fetch user-agent browser umum dari useragents.me -> ua.txt"
    )
    parser.add_argument("--timeout", type=int, default=10, help="Timeout per request dalam detik (default: 10)")
    parser.add_argument("--retries", type=int, default=3,  help="Jumlah retry per request (default: 3)")
    parser.add_argument("--dry-run", action="store_true",  help="Fetch data tapi TIDAK menulis file")
    args = parser.parse_args()

    start_time = time.time()
    print("================================================================")
    print("        UA SCRAPER -- useragents.me -> ua.txt")
    print("                  Author: SoraDev-ID")
    print("================================================================\n")

    session = create_session(timeout=args.timeout, retries=args.retries)

    all_uas, fetch_errors = fetch_all_ua(session)
    unique_uas = sorted(set(all_uas))
    duration = time.time() - start_time

    print(f"\n[i] Total unik (desktop + mobile gabungan): {len(unique_uas)} UA")
    print(f"[i] Sumber gagal: {fetch_errors if fetch_errors else 'tidak ada'}\n")

    if not unique_uas:
        status_str = "failed -- semua sumber tidak dapat dijangkau"
        print(f"[!] GAGAL: {status_str}", file=sys.stderr)
        if not args.dry_run:
            write_last_updated(0, duration, status_str, LAST_UPDATED_FILE)
        sys.exit(1)

    if fetch_errors:
        status_str = f"partial -- {len(fetch_errors)} sumber gagal: {', '.join(fetch_errors)}"
    else:
        status_str = "success"

    if args.dry_run:
        print("[DRY-RUN] 10 UA pertama yang akan ditulis ke ua.txt:")
        for ua in unique_uas[:10]:
            print(f"  {ua}")
        if len(unique_uas) > 10:
            print(f"  ... dan {len(unique_uas) - 10} lainnya.")
        print("\n[DRY-RUN] Tidak ada file yang ditulis.")
        return

    print(f"[*] Menulis {len(unique_uas)} UA ke {OUTPUT_FILE.name} ...")
    written = write_ua_file(unique_uas, OUTPUT_FILE)
    print(f"[OK] {written} baris berhasil ditulis ke {OUTPUT_FILE.name}")

    write_last_updated(written, duration, status_str, LAST_UPDATED_FILE)
    print(f"[OK] last_updated.txt diperbarui.")

    print("\n================================================================")
    print("                       RINGKASAN")
    print("================================================================")
    print(f"  * ua.txt             : {written:>6} user-agent")
    print(f"  * Sumber berhasil    : {len(UA_SOURCES) - len(fetch_errors)}/{len(UA_SOURCES)}")
    print(f"  * Status             : {status_str}")
    print(f"  * Durasi             : {duration:.2f} detik")
    print("================================================================")
    print("[OK] Selesai!\n")


if __name__ == "__main__":
    main()
