import os
import sys
import json
import time
import math
import random
import asyncio
import subprocess
from telethon import TelegramClient
from telethon.sessions import MemorySession
from telethon.tl.types import InputFileBig, InputFile
from telethon.tl.functions.upload import SaveBigFilePartRequest, SaveFilePartRequest

# Neutralize Telethon's internal update loop to prevent buggy update differences and unwanted disconnects
async def _dummy_update_loop(self):
    while self.is_connected():
        await asyncio.sleep(60)

TelegramClient._update_loop = _dummy_update_loop

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
    raw_parts = [p.strip() for p in file_info["path"].split("/") if p.strip()]
    cand = os.path.join(DOWNLOADS_DIR, *raw_parts)
    if os.path.exists(cand) and os.path.getsize(cand) > 1000:
        return cand
    if len(raw_parts) >= 2:
        parent_folder = clean_name(raw_parts[-2]).lower().strip()
        fname = clean_name(raw_parts[-1]).lower().strip()
        for root, _, files in os.walk(DOWNLOADS_DIR):
            p_name = clean_name(os.path.basename(root)).lower().strip()
            if p_name == parent_folder:
                for fl in files:
                    if clean_name(fl).lower().strip() == fname:
                        fp = os.path.join(root, fl)
                        if os.path.getsize(fp) > 1000:
                            return fp
    for root, _, files in os.walk(DOWNLOADS_DIR):
        for fl in files:
            if fl == name or clean_name(fl) == clean_name(name):
                fp = os.path.join(root, fl)
                if os.path.getsize(fp) > 1000:
                    return fp
    return None

async def ensure_connected(client):
    while not client.is_connected():
        try:
            await client.connect()
            if not await client.is_user_authorized():
                await client.start(bot_token=TOKEN)
            return True
        except Exception:
            await asyncio.sleep(2)
    return True

async def fast_upload_stream(client, file_path, concurrency=16):
    file_size = os.path.getsize(file_path)
    part_size = 512 * 1024
    part_count = math.ceil(file_size / part_size)
    is_big = file_size > 10 * 1024 * 1024
    file_id = random.getrandbits(63)
    file_name = os.path.basename(file_path)

    queue = asyncio.Queue(maxsize=concurrency * 2)
    done_counter = [0]
    counter_lock = asyncio.Lock()
    upload_error = [None]
    t_start = time.time()

    async def reader():
        with open(file_path, "rb") as f:
            for part_index in range(part_count):
                if upload_error[0]:
                    break
                data = f.read(part_size)
                await queue.put((part_index, data))
        for _ in range(concurrency):
            await queue.put(None)

    async def uploader():
        while True:
            item = await queue.get()
            if item is None:
                queue.task_done()
                break
            part_index, data = item
            success = False
            try:
                for attempt in range(8):
                    try:
                        if not client.is_connected():
                            await ensure_connected(client)
                        if is_big:
                            req = SaveBigFilePartRequest(file_id, part_index, part_count, data)
                        else:
                            req = SaveFilePartRequest(file_id, part_index, data)
                        await asyncio.wait_for(client(req), timeout=30)
                        success = True
                        break
                    except Exception as pe:
                        if attempt >= 7:
                            upload_error[0] = pe
                            print(f"\n⚠️ Part {part_index} failed: {pe}", flush=True)
                        await asyncio.sleep(1 + attempt)

                if success:
                    async with counter_lock:
                        done_counter[0] += 1
                        d = done_counter[0]
                        if d % 15 == 0 or d == part_count:
                            elapsed = time.time() - t_start
                            mb_done = (d * part_size) / (1024 * 1024)
                            sz_mb = file_size / (1024 * 1024)
                            pct = (d / part_count) * 100
                            cur_speed = mb_done / elapsed if elapsed > 0 else 0
                            print(f"  ⚡ {file_name[:24]}... [{d}/{part_count}] ({pct:.0f}%) -> {mb_done:.1f}/{sz_mb:.1f} MB @ {cur_speed:.2f} MB/s", flush=True)
            finally:
                queue.task_done()

    reader_task = asyncio.create_task(reader())
    uploader_tasks = [asyncio.create_task(uploader()) for _ in range(concurrency)]

    await reader_task
    await queue.join()
    await asyncio.gather(*uploader_tasks)

    if upload_error[0]:
        raise upload_error[0]

    name = os.path.basename(file_path)
    if is_big:
        return InputFileBig(file_id, part_count, name)
    else:
        return InputFile(file_id, part_count, name, md5_checksum="")

def sync_cache_to_git(cached_count):
    try:
        print(f"🚀 Auto-syncing cache ({cached_count} books) to Render...", flush=True)
        subprocess.run(["git", "add", TG_CACHE_PATH], cwd=BASE_DIR, check=False)
        subprocess.run(["git", "commit", "-m", f"Auto-sync cache ({cached_count} books)"], cwd=BASE_DIR, check=False)
        subprocess.run(["git", "push", "origin", "main"], cwd=BASE_DIR, check=False)
        print("✅ Synced with Render cloud!", flush=True)
    except Exception as ge:
        print("Git error:", ge, flush=True)

async def main():
    with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    uncached = [f for f in manifest if f["id"] not in tg_cache]
    print("=" * 55, flush=True)
    print(f"  StudyMate BOOSTED Turbo Uploader (MemorySession 16x) ", flush=True)
    print("=" * 55, flush=True)
    print(f"Total manifest files: {len(manifest)}", flush=True)
    print(f"Already cached: {len(tg_cache)}", flush=True)
    print(f"Remaining uncached: {len(uncached)}", flush=True)
    print("=" * 55, flush=True)

    if not uncached:
        print("🎉 All 1,376 files are already cached! Nothing to do.", flush=True)
        return

    items_to_upload = []
    for f_info in uncached:
        local_path = find_local_file(f_info)
        if local_path and os.path.exists(local_path):
            sz_mb = os.path.getsize(local_path) / (1024 * 1024)
            items_to_upload.append((f_info, local_path, sz_mb))
        else:
            print(f"⚠️ Missing locally: {f_info['name']}", flush=True)

    items_to_upload.sort(key=lambda x: x[2])
    print(f"Queue prepared: {len(items_to_upload)} files ready to boost!", flush=True)

    client = TelegramClient(MemorySession(), API_ID, API_HASH, receive_updates=False)
    await client.start(bot_token=TOKEN)
    print("⚡ Dedicated Turbo MTProto client connected via MemorySession! Peak speed unlocked.", flush=True)

    uploaded_since_push = 0
    total_to_do = len(items_to_upload)

    for i, (f_info, local_path, sz_mb) in enumerate(items_to_upload, 1):
        fid = f_info["id"]
        name = clean_name(f_info["name"])

        raw_parts = [p.strip() for p in f_info.get("path", "").split("/") if p.strip()]
        parent_name = clean_name(raw_parts[-2]) if len(raw_parts) >= 2 else ""
        if name.lower().startswith("part ") or len(name) <= 12:
            caption = f"📘 {parent_name} - {name}"
        else:
            caption = f"📘 {name}"
        if len(caption) > 1000:
            caption = caption[:995] + "..."

        print(f"\n▶️ Starting [{i}/{total_to_do}] {name} ({sz_mb:.1f} MB)...", flush=True)

        success = False
        for attempt in range(4):
            try:
                await ensure_connected(client)
                t0 = time.time()
                input_file = await fast_upload_stream(client, local_path, concurrency=16)
                msg = await client.send_file(CHANNEL_ID, input_file, caption=caption)
                dt = time.time() - t0
                speed_mbs = sz_mb / dt if dt > 0 else 0

                if msg and msg.id:
                    tg_cache[fid] = msg.id
                    uploaded_since_push += 1

                    with open(TG_CACHE_PATH, "w", encoding="utf-8") as cf:
                        json.dump(tg_cache, cf, indent=2)

                    curr_cached = len(tg_cache)
                    print(f"✅ [{i}/{total_to_do}] [⚡ {dt:.1f}s ({speed_mbs:.2f} MB/s)] {name} -> Msg ID: {msg.id} [Total Cached: {curr_cached}/1376]", flush=True)

                    if uploaded_since_push >= 5 or curr_cached == len(manifest):
                        sync_cache_to_git(curr_cached)
                        uploaded_since_push = 0

                    success = True
                    await asyncio.sleep(0.5)
                    break
            except Exception as e:
                print(f"Attempt {attempt+1} failed for {name}: {e}", flush=True)
                await asyncio.sleep(2)

        if not success:
            print(f"❌ Failed to upload {name} after 4 attempts", flush=True)

    if uploaded_since_push > 0:
        sync_cache_to_git(len(tg_cache))

    await client.disconnect()
    print("=" * 55, flush=True)
    print(f"🎉 BOOSTED UPLOAD COMPLETE! Total Cached: {len(tg_cache)}/{len(manifest)}", flush=True)
    print("=" * 55, flush=True)

if __name__ == "__main__":
    asyncio.run(main())
