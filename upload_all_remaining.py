import os
import sys
import json
import time
import math
import random
import asyncio
import subprocess
from telethon import TelegramClient
from telethon.tl.types import InputFileBig, InputFile
from telethon.tl.functions.upload import SaveBigFilePartRequest, SaveFilePartRequest

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

cache_lock = asyncio.Lock()
print_lock = asyncio.Lock()
uploaded_count = 0
uploaded_since_push = 0

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

async def ensure_connected(client, session_name):
    while not client.is_connected():
        print(f"[{session_name}] Reconnecting...", flush=True)
        try:
            await client.connect()
            if not await client.is_user_authorized():
                await client.start(bot_token=TOKEN)
            print(f"[{session_name}] Reconnected successfully!", flush=True)
            return True
        except Exception as e:
            print(f"[{session_name}] Reconnect failed: {e}. Retrying in 5s...", flush=True)
            await asyncio.sleep(5)
    return True

async def fast_upload(client, file_path, session_name, max_workers=6):
    file_size = os.path.getsize(file_path)
    part_size = 512 * 1024
    part_count = math.ceil(file_size / part_size)
    is_big = file_size > 10 * 1024 * 1024
    file_id = random.getrandbits(63)

    semaphore = asyncio.Semaphore(max_workers)

    async def upload_part(part_index, data):
        async with semaphore:
            for _ in range(3):
                try:
                    if not client.is_connected():
                        await ensure_connected(client, session_name)
                    if is_big:
                        req = SaveBigFilePartRequest(file_id, part_index, part_count, data)
                    else:
                        req = SaveFilePartRequest(file_id, part_index, data)
                    await client(req)
                    return
                except Exception:
                    await asyncio.sleep(1)

    tasks = []
    with open(file_path, "rb") as f:
        for i in range(part_count):
            data = f.read(part_size)
            tasks.append(upload_part(i, data))

    await asyncio.gather(*tasks)

    name = os.path.basename(file_path)
    if is_big:
        return InputFileBig(file_id, part_count, name)
    else:
        return InputFile(file_id, part_count, name, md5_checksum="")

async def worker(worker_id, queue, total):
    global uploaded_count, uploaded_since_push
    session_name = f"telethon_worker_{worker_id}"
    client = TelegramClient(session_name, API_ID, API_HASH)
    await client.start(bot_token=TOKEN)

    async with print_lock:
        print(f"Worker {worker_id} ready and connected!", flush=True)

    while True:
        try:
            item = queue.get_nowait()
        except asyncio.QueueEmpty:
            break

        idx, (f_info, local_path, sz_mb) = item
        fid = f_info["id"]
        name = clean_name(f_info["name"])

        success = False
        for attempt in range(3):
            try:
                await ensure_connected(client, session_name)
                caption = f"📘 {name}"
                if len(caption) > 1000:
                    caption = caption[:995] + "..."

                t0 = time.time()
                input_file = await fast_upload(client, local_path, session_name, max_workers=6)
                msg = await client.send_file(
                    CHANNEL_ID,
                    input_file,
                    caption=caption
                )
                dt = time.time() - t0

                if msg and msg.id:
                    async with cache_lock:
                        tg_cache[fid] = msg.id
                        uploaded_count += 1
                        uploaded_since_push += 1
                        curr_cached = len(tg_cache)
                        
                        try:
                            with open(TG_CACHE_PATH, "w", encoding="utf-8") as cf:
                                json.dump(tg_cache, cf, indent=2)
                        except Exception as ce:
                            print("Error saving cache:", ce)

                        need_push = (uploaded_since_push >= 10)
                        if need_push:
                            uploaded_since_push = 0

                    speed_mbs = sz_mb / dt if dt > 0 else 0
                    async with print_lock:
                        print(f"[W{worker_id}] [{uploaded_count}/{total}] [TURBO ⚡ {dt:.1f}s ({speed_mbs:.2f} MB/s)] {name} ({sz_mb:.1f} MB) -> Msg ID: {msg.id}", flush=True)

                    if need_push:
                        try:
                            async with print_lock:
                                print(f"🚀 Auto-syncing cache ({curr_cached} books) to Render...", flush=True)
                            subprocess.run(["git", "add", TG_CACHE_PATH], cwd=BASE_DIR, check=False)
                            subprocess.run(["git", "commit", "-m", f"Auto-sync cache ({curr_cached} books)"], cwd=BASE_DIR, check=False)
                            subprocess.run(["git", "push", "origin", "main"], cwd=BASE_DIR, check=False)
                            async with print_lock:
                                print("✅ Synced with Render cloud!", flush=True)
                        except Exception as ge:
                            print("Git error:", ge)

                    success = True
                    await asyncio.sleep(1.5)
                    break
            except Exception as e:
                err_str = str(e).lower()
                async with print_lock:
                    print(f"[W{worker_id}] Attempt {attempt+1} failed for {name}: {e}", flush=True)
                if "flood" in err_str or "wait" in err_str:
                    import re
                    m = re.search(r'(\d+)\s*second', err_str)
                    wait_s = int(m.group(1)) + 2 if m else 30
                    await asyncio.sleep(wait_s)
                elif "disconnected" in err_str:
                    await asyncio.sleep(3)
                    await ensure_connected(client, session_name)
                else:
                    await asyncio.sleep(5)

        if not success:
            async with print_lock:
                print(f"[W{worker_id}] [SKIP] Failed: {name}", flush=True)

        queue.task_done()

    await client.disconnect()

async def main():
    print("==================================================", flush=True)
    print("  StudyMate Dual-Worker Turbo Parallel Uploader   ", flush=True)
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

    queue = asyncio.Queue()
    for idx, item in enumerate(to_upload, 1):
        queue.put_nowait((idx, item))

    # Run 2 independent workers concurrently
    workers = [
        asyncio.create_task(worker(1, queue, total)),
        asyncio.create_task(worker(2, queue, total))
    ]

    await asyncio.gather(*workers)

    # Final sync
    try:
        subprocess.run(["git", "add", TG_CACHE_PATH], cwd=BASE_DIR, check=False)
        subprocess.run(["git", "commit", "-m", f"Final 100% cache sync ({len(tg_cache)} books)"], cwd=BASE_DIR, check=False)
        subprocess.run(["git", "push", "origin", "main"], cwd=BASE_DIR, check=False)
    except Exception:
        pass

    print(f"\n🎉 ALL UPLOADS COMPLETED! Total cached in library: {len(tg_cache)} books!", flush=True)

if __name__ == '__main__':
    asyncio.run(main())
