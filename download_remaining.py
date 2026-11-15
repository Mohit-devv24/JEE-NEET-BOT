import os
import sys
import json
import time
import socket
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
from googleapiclient.errors import HttpError

socket.setdefaulttimeout(180)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TOKEN_FILE = os.path.join(BASE_DIR, 'token.json')
MANIFEST_FILE = os.path.join(BASE_DIR, 'files_manifest.json')
OUTPUT_DIR = os.path.join(BASE_DIR, 'downloaded_files')

thread_local = threading.local()

def clean_path(path_str):
    parts = path_str.split("/")
    cleaned = []
    for p in parts:
        p = p.strip()
        p = p.replace("ðŸ“š", "Books").replace("âžª", "-").replace("Ar!hant", "Arihant")
        cleaned.append(p)
    return "/".join(cleaned)

def clean_name(s):
    return s.replace("ðŸ“š", "Books").replace("âžª", "-").replace("Ar!hant", "Arihant").strip()

def get_credentials():
    creds = Credentials.from_authorized_user_file(TOKEN_FILE, ['https://www.googleapis.com/auth/drive.readonly'])
    if not creds.valid and creds.expired and creds.refresh_token:
        creds.refresh(Request())
        with open(TOKEN_FILE, 'w') as f:
            f.write(creds.to_json())
    return creds

def get_drive_service(creds):
    if not hasattr(thread_local, "service"):
        thread_local.service = build('drive', 'v3', credentials=creds, cache_discovery=False)
    return thread_local.service

print_lock = threading.Lock()
completed_count = 0

def download_file(item, creds, total):
    global completed_count
    file_id = item["id"]
    file_name = item["name"]
    rel_path = clean_path(item["path"])
    dest_path = os.path.join(OUTPUT_DIR, rel_path)

    if os.path.exists(dest_path) and os.path.getsize(dest_path) > 1024:
        with print_lock:
            completed_count += 1
            print(f"[{completed_count}/{total}] [SKIP] {file_name}", flush=True)
        return True

    os.makedirs(os.path.dirname(dest_path), exist_ok=True)
    temp_path = dest_path + f".tmp_{threading.get_ident()}"
    service = get_drive_service(creds)

    for attempt in range(1, 5):
        try:
            request = service.files().get_media(fileId=file_id, supportsAllDrives=True)
            with open(temp_path, "wb") as fh:
                downloader = MediaIoBaseDownload(fh, request, chunksize=10*1024*1024)
                done = False
                while not done:
                    status, done = downloader.next_chunk()
            os.rename(temp_path, dest_path)
            size_mb = os.path.getsize(dest_path) / (1024 * 1024)
            with print_lock:
                completed_count += 1
                print(f"[{completed_count}/{total}] [OK] {file_name} ({size_mb:.1f} MB)", flush=True)
            return True
        except Exception as e:
            if os.path.exists(temp_path):
                os.remove(temp_path)
            if attempt == 4:
                with print_lock:
                    print(f"[FAIL] {file_name}: {e}", flush=True)
            time.sleep(3 * attempt)

    return False

def main():
    creds = get_credentials()
    with open(MANIFEST_FILE, "r") as f:
        manifest = json.load(f)

    local_files = set()
    for root, _, files in os.walk(OUTPUT_DIR):
        for fl in files:
            if not fl.startswith(".") and os.path.getsize(os.path.join(root, fl)) > 1024:
                local_files.add(fl.lower())
                local_files.add(clean_name(fl).lower())

    missing = []
    for item in manifest:
        name = item["name"]
        clean_n = clean_name(name)
        if name.lower() not in local_files and clean_n.lower() not in local_files:
            missing.append(item)

    total = len(missing)
    print(f"Starting targeted download for {total} remaining files with 2 workers...\n", flush=True)

    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = [executor.submit(download_file, item, creds, total) for item in missing]
        for f in as_completed(futures):
            pass

    print("\nTargeted Download Finished!", flush=True)

if __name__ == '__main__':
    main()
