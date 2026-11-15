import os
import sys
import json
import io
import time
import socket
import threading

# Prevent socket timeouts on large files (500MB+)
socket.setdefaulttimeout(120)
from concurrent.futures import ThreadPoolExecutor, as_completed
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
from googleapiclient.errors import HttpError

SCOPES = ['https://www.googleapis.com/auth/drive.readonly']
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CLIENT_SECRET_FILE = os.path.join(BASE_DIR, 'client_secret.json')
TOKEN_FILE = os.path.join(BASE_DIR, 'token.json')
MANIFEST_FILE = os.path.join(BASE_DIR, 'files_manifest.json')
OUTPUT_DIR = os.path.join(BASE_DIR, 'downloaded_files')

# Thread local for Drive API service
thread_local = threading.local()

def clean_path(path_str):
    parts = path_str.split("/")
    cleaned = []
    for p in parts:
        p = p.strip()
        p = p.replace("ðŸ“š", "Books").replace("âžª", "-").replace("Ar!hant", "Arihant")
        cleaned.append(p)
    return "/".join(cleaned)

def get_credentials():
    creds = None
    if os.path.exists(TOKEN_FILE):
        try:
            creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
        except Exception:
            creds = None

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            print("Refreshing expired credentials...", flush=True)
            creds.refresh(Request())
        else:
            print("Starting OAuth flow...", flush=True)
            flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRET_FILE, SCOPES)
            creds = flow.run_local_server(port=0)
            
        with open(TOKEN_FILE, 'w') as token:
            token.write(creds.to_json())

    return creds

def get_drive_service(creds):
    if not hasattr(thread_local, "service"):
        thread_local.service = build('drive', 'v3', credentials=creds, cache_discovery=False)
    return thread_local.service

print_lock = threading.Lock()
completed_count = 0
total_files = 0

def download_task(item, creds):
    global completed_count
    file_id = item["id"]
    file_name = item["name"]
    rel_path = clean_path(item["path"])
    dest_path = os.path.join(OUTPUT_DIR, rel_path)

    # If already downloaded
    if os.path.exists(dest_path) and os.path.getsize(dest_path) > 1024:
        with print_lock:
            completed_count += 1
            size_mb = os.path.getsize(dest_path) / (1024 * 1024)
            print(f"[{completed_count}/{total_files}] [SKIP] {file_name} ({size_mb:.1f} MB)", flush=True)
        return True

    os.makedirs(os.path.dirname(dest_path), exist_ok=True)
    temp_path = dest_path + f".tmp_{threading.get_ident()}"

    service = get_drive_service(creds)

    for attempt in range(1, 4):
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
                print(f"[{completed_count}/{total_files}] [OK] {file_name} ({size_mb:.1f} MB)", flush=True)
            return True
        except HttpError as error:
            if os.path.exists(temp_path):
                os.remove(temp_path)
            if attempt == 3:
                with print_lock:
                    print(f"[FAIL HTTP] {file_name}: {error}", flush=True)
            time.sleep(2 * attempt)
        except Exception as e:
            if os.path.exists(temp_path):
                os.remove(temp_path)
            if attempt == 3:
                with print_lock:
                    print(f"[FAIL] {file_name}: {e}", flush=True)
            time.sleep(2 * attempt)

    return False

def main():
    global total_files
    print("==================================================", flush=True)
    print("  StudyMate TURBO Multi-Thread Downloader (6x)    ", flush=True)
    print("==================================================", flush=True)

    creds = get_credentials()

    with open(MANIFEST_FILE, "r") as f:
        files = json.load(f)

    # Sort files
    files.sort(key=lambda x: clean_path(x["path"]).lower())
    total_files = len(files)
    print(f"Total files in queue: {total_files}\n", flush=True)

    # Run with 6 parallel worker threads
    MAX_WORKERS = 6
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = [executor.submit(download_task, item, creds) for item in files]
        for f in as_completed(futures):
            pass

    print("\n==================================================", flush=True)
    print("TURBO Download Pass Completed!", flush=True)
    print("==================================================", flush=True)

if __name__ == '__main__':
    main()
