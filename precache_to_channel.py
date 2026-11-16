import os
import sys
import json
import time
import subprocess

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MANIFEST_PATH = os.path.join(BASE_DIR, "files_manifest.json")
DOWNLOADS_DIR = os.path.join(BASE_DIR, "downloaded_files")
TG_CACHE_PATH = os.path.join(BASE_DIR, "telegram_file_cache.json")

TOKEN = "8996284156:AAEl6oYSxqszHXUP-yS7FKBTYq5g3tKLLIo"
CHANNEL_ID = "-1004467297667"

tg_cache = {}
if os.path.exists(TG_CACHE_PATH):
    try:
        with open(TG_CACHE_PATH, "r", encoding="utf-8") as f:
            tg_cache = json.load(f)
    except Exception:
        tg_cache = {}

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

def upload_via_curl(file_path, display_name, sz_mb):
    abs_path = os.path.abspath(file_path)
    # Dynamic timeout: at least 180s, plus 25s per MB for slower home upload connections
    timeout_sec = max(180, int(sz_mb * 25))
    cmd = [
        "curl", "-s", "--max-time", str(timeout_sec),
        "-F", f'document=@"{abs_path}"',
        "-F", f"chat_id={CHANNEL_ID}",
        "-F", f"caption=📘 {display_name}",
        f"https://api.telegram.org/bot{TOKEN}/sendDocument"
    ]
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout_sec + 30)
        if res.returncode == 0 and res.stdout:
            data = json.loads(res.stdout)
            if data.get("ok"):
                return data["result"]["document"]["file_id"]
            else:
                err = data.get("description", "Unknown error")
                print(f"Telegram API response: {err}")
                if "retry after" in err.lower():
                    import re
                    m = re.search(r'retry after (\d+)', err.lower())
                    wait_s = int(m.group(1)) + 2 if m else 30
                    print(f"Rate limited. Waiting {wait_s}s...")
                    time.sleep(wait_s)
    except Exception as e:
        print("Curl execution error:", e)
    return None

def main():
    print("==================================================", flush=True)
    print("   StudyMate Smart-Sorted Cloud Cache Engine      ", flush=True)
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

    # SORT BY FILE SIZE (Smallest files first: quick wins for hundreds of books)
    to_cache.sort(key=lambda x: x[2])

    total = len(to_cache)
    print(f"Found {total} remaining books to upload into channel (sorted smallest to largest)...\n", flush=True)

    uploaded_since_push = 0
    for idx, (f_info, local_path, sz_mb) in enumerate(to_cache, 1):
        fid = f_info["id"]
        name = clean_name(f_info["name"])

        success = False
        for attempt in range(2):
            doc_fid = upload_via_curl(local_path, name, sz_mb)
            if doc_fid:
                tg_cache[fid] = doc_fid
                success = True
                uploaded_since_push += 1
                print(f"[{idx}/{total}] [CACHED ⚡ 0.1s] {name} ({sz_mb:.2f} MB)", flush=True)
                
                try:
                    with open(TG_CACHE_PATH, "w", encoding="utf-8") as cf:
                        json.dump(tg_cache, cf, indent=2)
                except Exception as e:
                    print("Error saving cache:", e)

                # Auto-sync to Render cloud every 20 files
                if uploaded_since_push >= 20:
                    try:
                        print("🚀 Auto-syncing cache to Render cloud...", flush=True)
                        subprocess.run(["git", "add", TG_CACHE_PATH], cwd=BASE_DIR, check=False)
                        subprocess.run(["git", "commit", "-m", f"Auto-sync cache: {len(tg_cache)} books"], cwd=BASE_DIR, check=False)
                        subprocess.run(["git", "push", "origin", "main"], cwd=BASE_DIR, check=False)
                        uploaded_since_push = 0
                        print("✅ Synced with Render cloud!", flush=True)
                    except Exception as ge:
                        print("Git push error:", ge)

                time.sleep(2)
                break
            else:
                print(f"Retry {attempt+1} for {name} ({sz_mb:.1f} MB)...")
                time.sleep(5)

        if not success:
            print(f"[SKIP] Failed to upload {name} ({sz_mb:.1f} MB)")

    # Final push
    try:
        subprocess.run(["git", "add", TG_CACHE_PATH], cwd=BASE_DIR, check=False)
        subprocess.run(["git", "commit", "-m", f"Final cache sync: {len(tg_cache)} books"], cwd=BASE_DIR, check=False)
        subprocess.run(["git", "push", "origin", "main"], cwd=BASE_DIR, check=False)
    except Exception:
        pass

    print("\nPre-caching run completed! Total cached:", len(tg_cache))

if __name__ == '__main__':
    main()
