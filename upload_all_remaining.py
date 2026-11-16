import os
import sys
import json
import time
import asyncio
import subprocess
from telethon import TelegramClient

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MANIFEST_PATH = os.path.join(BASE_DIR, "files_manifest.json")
DOWNLOADS_DIR = os.path.join(BASE_DIR, "downloaded_files")
TG_CACHE_PATH = os.path.join(BASE_DIR, "telegram_file_cache.json")

API_ID = 38678516
API_HASH = "68453370d1d55ec8bb7a702e9a511de4"
TOKEN = "8996284156:AAEl6oYSxqszHXUP-yS7FKBTYq5g3tKLLIo"
CHANNEL_ID = -1004467297667

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

async def main():
    print("==================================================", flush=True)
    print("   StudyMate 100% Full Library Turbo Uploader     ", flush=True)
    print("==================================================", flush=True)

    with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
        files = json.load(f)

    to_upload = []
    for f in files:
        fid = f["id"]
        if fid not in tg_cache and not f.get("is_folder", False):
            lp = find_local_file(f)
            if lp and os.path.exists(lp):
                sz_mb = os.path.getsize(lp) / (1024 * 1024)
                to_upload.append((f, lp, sz_mb))

    to_upload.sort(key=lambda x: x[2]) # Smallest to largest
    total = len(to_upload)
    print(f"Total uncached files remaining: {total}\n", flush=True)

    client = TelegramClient("telethon_full_uploader", API_ID, API_HASH)
    await client.start(bot_token=TOKEN)
    print("Telethon MTProto connected! Starting rapid uploads...\n", flush=True)

    uploaded_since_push = 0
    for idx, (f_info, local_path, sz_mb) in enumerate(to_upload, 1):
        fid = f_info["id"]
        name = clean_name(f_info["name"])

        success = False
        for attempt in range(2):
            try:
                caption = f"📘 {name} ({sz_mb:.1f} MB)"
                if len(caption) > 1000:
                    caption = caption[:995] + "..."
                msg = await client.send_file(
                    CHANNEL_ID,
                    local_path,
                    caption=caption
                )
                if msg and msg.id:
                    tg_cache[fid] = msg.id
                    success = True
                    uploaded_since_push += 1
                    print(f"[{idx}/{total}] [CACHED ⚡] {name} ({sz_mb:.1f} MB) -> Msg ID: {msg.id}", flush=True)

                    with open(TG_CACHE_PATH, "w", encoding="utf-8") as cf:
                        json.dump(tg_cache, cf, indent=2)

                    if uploaded_since_push >= 10:
                        try:
                            print("🚀 Auto-syncing cache to Render...", flush=True)
                            subprocess.run(["git", "add", TG_CACHE_PATH, "bot.py"], cwd=BASE_DIR, check=False)
                            subprocess.run(["git", "commit", "-m", f"Auto-sync cache ({len(tg_cache)} books)"], cwd=BASE_DIR, check=False)
                            subprocess.run(["git", "push", "origin", "main"], cwd=BASE_DIR, check=False)
                            uploaded_since_push = 0
                            print("✅ Synced with Render cloud!", flush=True)
                        except Exception as ge:
                            print("Git error:", ge)

                    await asyncio.sleep(1.5)
                    break
            except Exception as e:
                err_str = str(e).lower()
                print(f"Attempt {attempt+1} failed for {name}: {e}", flush=True)
                if "flood" in err_str or "wait" in err_str:
                    await asyncio.sleep(30)
                else:
                    await asyncio.sleep(5)

        if not success:
            print(f"[SKIP] Failed: {name}", flush=True)

    # Final sync
    try:
        subprocess.run(["git", "add", TG_CACHE_PATH, "bot.py"], cwd=BASE_DIR, check=False)
        subprocess.run(["git", "commit", "-m", f"Final 100% cache sync ({len(tg_cache)} books)"], cwd=BASE_DIR, check=False)
        subprocess.run(["git", "push", "origin", "main"], cwd=BASE_DIR, check=False)
    except Exception:
        pass

    await client.disconnect()
    print(f"\n🎉 ALL UPLOADS COMPLETED! Total cached in library: {len(tg_cache)} books!", flush=True)

if __name__ == '__main__':
    asyncio.run(main())
