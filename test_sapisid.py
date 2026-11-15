import requests
import time
import hashlib
import json

SAPISID = "9a7RR0s9ojt1SyTo/ADz-mnCRM_mUdyynd"
ORIGIN = "https://drive.google.com"

def get_sapisid_hash(sapisid, origin):
    now = str(int(time.time()))
    payload = f"{now} {sapisid} {origin}"
    sha1 = hashlib.sha1(payload.encode("utf-8")).hexdigest()
    return f"SAPISIDHASH {now}_{sha1}"

auth_header = get_sapisid_hash(SAPISID, ORIGIN)
print("Auth header:", auth_header)

COOKIE = "SID=g.a000EAmCGKFGdvsmC2VyCwQYQg_6Yr9gEoihrnGBrN_H31ibSKnIvYqll3Tb2FZibR_b_sTeMAACgYKAacSARcSFQHGX2Mi69exRtIiIeCcU3aFeCH6JhoVAUF8yKqjgMea789yDnp0KdtI-VEX0076; APISID=CuXt6up2acDmhMBB/AdiHJ3ky03ycG_tXH; SAPISID=9a7RR0s9ojt1SyTo/ADz-mnCRM_mUdyynd; __Secure-1PAPISID=9a7RR0s9ojt1SyTo/ADz-mnCRM_mUdyynd; __Secure-3PAPISID=9a7RR0s9ojt1SyTo/ADz-mnCRM_mUdyynd; SEARCH_SAMESITE=CgQIn6IB; OTZ=8872216_34_34__34_; SIDCC=APD_SKF86zzLHtLuSC-a84GDN7f1cE_t4oWld-ZS9KBMbckgtzaGGDE5cmK-dRTUyY-qiiJIBfnx"

headers = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Authorization": auth_header,
    "X-Goog-AuthUser": "0",
    "Origin": ORIGIN,
    "Cookie": COOKIE
}

# Test fetching metadata or download link for file 18: 1jw3G9MLg5gvdlpSe7tc77ALhrRIgZPR_
url = "https://drive.google.com/uc?id=1jw3G9MLg5gvdlpSe7tc77ALhrRIgZPR_&export=download"
r = requests.get(url, headers=headers, allow_redirects=False)
print("Status:", r.status_code)
print("Location:", r.headers.get("Location"))
print("Headers:", dict(r.headers))
