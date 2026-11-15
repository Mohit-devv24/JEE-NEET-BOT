import os
import shutil
import sqlite3
import hashlib
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend

PASSWORD = b"fRfJ4opfDJgQwjvAeDwKcw=="
SALT = b"saltysalt"
IV = b" " * 16
ITERATIONS = 1003
KEY_LEN = 16

key = hashlib.pbkdf2_hmac("sha1", PASSWORD, SALT, ITERATIONS, dklen=KEY_LEN)

cookie_db_path = os.path.expanduser("~/Library/Application Support/Google/Chrome/Default/Cookies")
temp_db_path = "/Users/mohitgoyal/Downloads/bopt/temp_cookies.sqlite"

shutil.copyfile(cookie_db_path, temp_db_path)

conn = sqlite3.connect(temp_db_path)
cursor = conn.cursor()

cursor.execute("""
    SELECT host_key, name, value, encrypted_value 
    FROM cookies 
    WHERE host_key LIKE '%google.com'
""")

def decrypt_value(enc_val):
    if not enc_val:
        return ""
    if enc_val[:3] == b"v10":
        enc_val = enc_val[3:]
    cipher = Cipher(algorithms.AES(key), modes.CBC(IV), backend=default_backend())
    decryptor = cipher.decryptor()
    decrypted = decryptor.update(enc_val) + decryptor.finalize()
    # Remove PKCS7 padding
    pad_len = decrypted[-1]
    if isinstance(pad_len, int) and pad_len < 16:
        decrypted = decrypted[:-pad_len]
    return decrypted.decode("utf-8", errors="ignore")

google_cookies = {}
for host, name, val, enc_val in cursor.fetchall():
    if val:
        v = val
    else:
        try:
            v = decrypt_value(enc_val)
        except Exception as e:
            continue
    google_cookies[name] = v

conn.close()
os.remove(temp_db_path)

print(f"Decrypted {len(google_cookies)} Google cookies!")
for k in ["SID", "HSID", "SSID", "SAPISID", "__Secure-1PSID", "__Secure-1PSIDTS", "OSID"]:
    if k in google_cookies:
        print(f" - {k}: {google_cookies[k][:15]}...")

# Save to a fresh cookies file
with open("/Users/mohitgoyal/Downloads/bopt/fresh_cookies.json", "w") as f:
    import json
    json.dump(google_cookies, f, indent=2)
print("Saved fresh_cookies.json!")
