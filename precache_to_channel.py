import os
import sys
import socket
import json
import time
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

# Force IPv4 on macOS to eliminate IPv6 DNS lag
_orig_getaddrinfo = socket.getaddrinfo
def _ipv4_getaddrinfo(*args, **kwargs):
    responses = _orig_getaddrinfo(*args, **kwargs)
    ipv4_res = [r for r in responses if r[0] == socket.AF_INET]
    return ipv4_res if ipv4_res else responses
socket.getaddrinfo = _ipv4_getaddrinfo

import telebot
from telebot import apihelper

apihelper.READ_TIMEOUT = 300
apihelper.CONNECT_TIMEOUT = 30
apihelper.CUSTOM_REQUEST_TIMEOUT = (30, 300)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MANIFEST_PATH = os.path.join(BASE_DIR, "files_manifest.json")
DOWNLOADS_DIR = os.path.join(BASE_DIR, "downloaded_files")
TG_CACHE_PATH = os.path.join(BASE_DIR, "telegram_file_cache.json")

TOKEN = "8996284156:AAEl6oYSxqszHXUP-yS7FKBTYq5g3tKLLIo"
bot = telebot.TeleBot(TOKEN, parse_mode="HTML")
CHANNEL_ID = -1004467297667

cache_lock = threading.Lock()
print_lock = threading.Lock()
cached_count = 0

tg_cache = {}
if os.path.exists(TG_CACHE_PATH):
    try:
        with open(TG_CACHE_PATH, "r", encoding="utf-8") as f:
            tg_cache = json.load(f)
    except Exception:
        tg_cache = {}

def save_cache():
    with cache_lock:
        try:
            with open(TG_CACHE_PATH, "w", encoding="utf-8") as f:
                json.dump(tg_cache, f, indent=2)
        except Exception as e:
            print("Error saving cache:", e)

def clean_name(s):
    if not s:
        return ""
    s = s.replace("ðŸ“š", "📚").replace("âžª", "➔").replace("Ar!hant", "Arihant")
    s = s.replace("ð", "").replace("â", "").replace("Â", "").replace("ï", "").strip()
    import re
    return re.sub(r'\s+', ' ', s)

def find_local_file(file_info):
    name = file_info["name"]
    clean_p = clean_name(file_info["path"])
    p1 = os.path.join(DOWNLOADS_DIR, clean_p)
    if os.path.exists(p1) and os.path.getsize(p1) > 1000:
        return p1
    p2 = os.path.join(DOWNLOADS_DIR, file_info["path"])
    if os.path.exists(p2) and os.path.getsize(p2) > 1000:
        return p2
    for root, _, files in os.walk(DOWNLOADS_DIR):
        for fl in files:
            if fl == name or clean_name(fl) == clean_name(name):
                fp = os.path.join(root, fl)
                if os.path.getsize(fp) > 1000:
                    return fp
    return None

def upload_single_file(item_tuple, total):
    global cached_count
    f_info, local_path, sz_mb = item_tuple
    fid = f_info["id"]
    name = clean_name(f_info["name"])

    for attempt in range(1, 4):
        try:
            with open(local_path, "rb") as doc:
                sent = bot.send_document(
                    CHANNEL_ID,
                    doc,
                    caption=f"📘 <b>{name}</b> ({sz_mb:.1f} MB)",
                    timeout=300
                )
            if sent and sent.document:
                with cache_lock:
                    tg_cache[fid] = sent.document.file_id
                    save_cache()
                    cached_count += 1
                    current = cached_count
                with print_lock:
                    print(f"[{current}/{total}] [CACHED ⚡ 0.2s] {name} ({sz_mb:.1f} MB)", flush=True)
            return True
        except Exception as e:
            err_str = str(e).lower()
            if "retry_after" in err_str or "too many requests" in err_str:
                import re
                wait_s = 20
                m = re.search(r'retry after (\d+)', err_str)
                if m:
                    wait_s = int(m.group(1)) + 2
                with print_lock:
                    print(f"Rate limited by Telegram for {name}. Waiting {wait_s}s...", flush=True)
                time.sleep(wait_s)
            else:
                if attempt == 3:
                    with print_lock:
                        print(f"[FAIL] {name}: {e}", flush=True)
                time.sleep(2 * attempt)
    return False

def main():
    print("==================================================", flush=True)
    print("  StudyMate Turbo Pre-Cache Engine (3x Parallel)  ", flush=True)
    print("==================================================", flush=True)

    with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
        files = json.load(f)

    to_cache = []
    for f in files:
        fid = f["id"]
        if fid not in tg_cache:
            lp = find_local_file(f)
            if lp and os.path.exists(lp):
                sz_mb = os.path.getsize(lp) / (1024 * 1024)
                if sz_mb <= 49.5:
                    to_cache.append((f, lp, sz_mb))

    total = len(to_cache)
    print(f"Found {total} remaining books to pre-cache with 3 parallel workers...\n", flush=True)

    with ThreadPoolExecutor(max_workers=3) as executor:
        futures = [executor.submit(upload_single_file, item, total) for item in to_cache]
        for f in as_completed(futures):
            pass

    print("\nTurbo Pre-caching Pass Completed! All books are now instant!", flush=True)

if __name__ == '__main__':
    main()
