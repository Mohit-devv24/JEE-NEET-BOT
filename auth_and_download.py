import os
import sys
import json
import io
import time
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
PROGRESS_FILE = os.path.join(BASE_DIR, 'download_progress_v2.json')

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
            print("Starting OAuth local authentication flow...", flush=True)
            flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRET_FILE, SCOPES)
            creds = flow.run_local_server(port=0)
            
        with open(TOKEN_FILE, 'w') as token:
            token.write(creds.to_json())
        print("Credentials saved to token.json!", flush=True)

    return creds

def download_file(service, file_id, dest_path, file_name, idx, total):
    # If already downloaded and > 1KB
    if os.path.exists(dest_path) and os.path.getsize(dest_path) > 1024:
        size_mb = os.path.getsize(dest_path) / (1024 * 1024)
        print(f"[{idx}/{total}] [SKIP] {file_name} ({size_mb:.2f} MB)", flush=True)
        return True

    os.makedirs(os.path.dirname(dest_path), exist_ok=True)
    temp_path = dest_path + ".tmp"

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
            print(f"[{idx}/{total}] [OK] {file_name} ({size_mb:.2f} MB)", flush=True)
            return True
        except HttpError as error:
            print(f"[{idx}/{total}] [HTTP ERROR attempt {attempt}] {file_name}: {error}", flush=True)
            if os.path.exists(temp_path):
                os.remove(temp_path)
            if attempt < 3:
                time.sleep(2)
        except Exception as e:
            print(f"[{idx}/{total}] [ERROR attempt {attempt}] {file_name}: {e}", flush=True)
            if os.path.exists(temp_path):
                os.remove(temp_path)
            if attempt < 3:
                time.sleep(2)

    return False

def main():
    print("==================================================", flush=True)
    print("  StudyMate - Google Drive Official Downloader   ", flush=True)
    print("==================================================", flush=True)

    creds = get_credentials()
    service = build('drive', 'v3', credentials=creds)

    with open(MANIFEST_FILE, "r") as f:
        files = json.load(f)

    # Sort strictly by cleaned path for serial order
    files.sort(key=lambda x: clean_path(x["path"]).lower())

    total = len(files)
    print(f"\nTotal files in serial queue: {total}\n", flush=True)

    success_count = 0
    fail_count = 0

    for idx, f in enumerate(files, 1):
        rel_path = clean_path(f["path"])
        dest_path = os.path.join(OUTPUT_DIR, rel_path)
        ok = download_file(service, f["id"], dest_path, f["name"], idx, total)
        if ok:
            success_count += 1
        else:
            fail_count += 1

    print("\n==================================================", flush=True)
    print(f"Download Finished! Total: {total} | Success: {success_count} | Failed: {fail_count}", flush=True)
    print("==================================================", flush=True)

if __name__ == '__main__':
    main()
