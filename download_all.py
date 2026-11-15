import os
import sys
import re
import json
import time
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed

COOKIE = """COMPASS=drive=CgAQz82o1wYauQEACWuJV-eznuhGsHSV6P6wiJ49ncDLhMC5eNDQ7XfyfC0e4qXZGMB8IrxVa51JL4FjVB21y5z9PAqJYDBD-g4TEVrvG4WtxMeooMEcK2DvGqORRbDlH2yhTD55nYIcif1s1CyqeKc9_5ymuDFnsezAieeVnSbfslj3edSJH941IS_ru2s6T20hju-CThjrnA9c0vnk9498VD5ztO8-eBzhxF8EBg42Ws3OTzKUr7hmvdLUB1Co3b1bnzAB; HSID=AVyWlRqIF5kC_5_Wj; SSID=An0jexAMbFSnd0MwD; APISID=D00EXtKOuAG1OFB9/AT5RDekKMRu8NkfLD; SAPISID=DDlOF2Yd-g7Cdide/AUGgbKpei4bux2sep; __Secure-1PAPISID=DDlOF2Yd-g7Cdide/AUGgbKpei4bux2sep; __Secure-3PAPISID=DDlOF2Yd-g7Cdide/AUGgbKpei4bux2sep; SEARCH_SAMESITE=CgQI-qEB; OSID=g.a000EAnJGAyYEt20cRPJNcHOlZJWCTn3o8MYVMff2fVskkGZaLkbZPo0eA42WMUmN7AkAEy1QQACgYKATMSARMSFQHGX2MiM0vNpVDsxLMjR-IXKu3C1hoVAUF8yKrwvPq-2b55uc5U8MKM0Rgi0076; __Secure-OSID=g.a000EAnJGAyYEt20cRPJNcHOlZJWCTn3o8MYVMff2fVskkGZaLkbvg1RTz3eBO2x9i5WcZh9YAACgYKAfISARMSFQHGX2MiYwj4V_AkqKuY1vcrcLMYqhoVAUF8yKqPUcAA5UFoM86umuQpYiB-0076; SID=g.a000EQnJGAKTVvU2ZSlIPDm5eFNikgSnagM7oAPXBt7cyiPy7BBbYcAmSxytXe0_2yT7aXo78gACgYKAccSARMSFQHGX2MiHHGkGdlojGKUyH2NrAwS-hoVAUF8yKpxWR-ad6HVm6sUZ3UBISUy0076; __Secure-1PSID=g.a000EQnJGAKTVvU2ZSlIPDm5eFNikgSnagM7oAPXBt7cyiPy7BBbR7TqOTu8s94B9PmtMbvM5QACgYKAZUSARMSFQHGX2Mi4QTYub8fx_QAFZ6q2JsccxoVAUF8yKqUNl7Q3jSplwRQ3_3JheQs0076; __Secure-3PSID=g.a000EQnJGAKTVvU2ZSlIPDm5eFNikgSnagM7oAPXBt7cyiPy7BBbZdSEmZ4BuAtiJZHlVeB-7gACgYKAXESARMSFQHGX2MivADFvKTg62kK1GKwcmuTpBoVAUF8yKq--KQgD3m2MbTU4oCath3M0076; GCL_AW_P=GCL.1793624557.CjwKCAjwxrLHBhA2EiwAu9EdM8KRuXEni6idmvbbr0G7S_IUda_WByaWQ2aabNuzPt0y0MDkA5F1IRoC53IQAvD_BwE; AEC=Aaa9EJrHfQeqpWJUn_RP0sSKSFNqqZ-CLsnKbz1btf-0ejtykF3LS5cpZD0; NID=CsADCAES8gIBM9Agl7h7U897SGuXJjv5CF7q90q8c3tmAtS0KP2QBcfupN1EJsjIdsfpC3ZrpH681Ha95aap4IlTgd206GY89x86XlfeoJ_uYGgO2lLf7SnYgilEOyc_uS1qpuWgiqSG4LUyt_SBVauQZeznF750nOHAD_YxgmqA7NGKLdNEyahE1TiLq3r2E5RCBErbWEBnQbT2fA1yeC5HIsf6tz7e0zWqxZxBprHvk0YxzxjZimbUjlxoNBiTaNHiQz_zhLY2mYE1MNnZZOosgywUQRCv8IHjGeGrP2ECys1z65VTOIq64rWYoHhJ9CZI9LMhPq03syRm8hqLFXUT5bHC-Nwagjb7VGtGnSAqpxow9j8BSkCgzQ4v2On-IUbCKxFMiqIMB6RvBZRV6ieENvupMKQ4aDFKHgvnjrCbM_OIxwMyDD4Hc1neisNVjCPInrh_RwE8rjC5jKhj6uVy_1PA4ykCFaLNV9GM2HLfSPQRX2vyHwfoKAEyRQFwSkLPOZa2TESMklusnlngQpkxvDwEEw3lwumTIXHn6UxRmtH7ZXN31gY0O0VW4JmYJJbc9XX4UfMX2jaxYIulOTMWBw; OTZ=8857034_34_34__34_; COMPASS=appsfrontendserver=CgAQ2M2o1wYagwEACWuJVwzi4WUYkrRbTB-TRu1gXWauEw0h_wi6kakpJ3Z5G0OB1WIZ3FQjjDqoqQQyD83EUmlsMKKwXvNURjgXFOhKfjABCdI_wuCaxw-SNWrTyf4W8_rcDWCDtaLFF7GuLGB9ScJxaU3-hN4nMYCN1Un1JDubcknez09PsGVKGCJpMyABMAE; __Secure-1PSIDTS=sidts-CjIBnJZzakvF-5oPiFJIY1htS2nGEcFrlyWo_r8u6r8JZKe6cimo-apnYkCqOjMdBh6xfhAA; __Secure-3PSIDTS=sidts-CjIBnJZzakvF-5oPiFJIY1htS2nGEcFrlyWo_r8u6r8JZKe6cimo-apnYkCqOjMdBh6xfhAA; SIDCC=APD_SKGvD0Y5qEkKh0JSItrWej_y3Jj91c_HIvBBpFVumIGVQvNklCO0jJWcAYspHPHtom6sw0s; __Secure-1PSIDCC=APD_SKE0V9gP6Qeb216x0E8Hkurbmh0PuWnk__5xgwPiaiNgcXC30Y_ZVcHtt2_l9d0P1mtvG4M; __Secure-3PSIDCC=APD_SKH2kylWUza7jLuQK-_DZEEEJaiQYwTCi7lLiOvltydInVCg7L1KgrntkA3RE1lzEcXpGxUH""".strip()

def create_session():
    s = requests.Session()
    s.headers.update({
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    })
    for item in COOKIE.split("; "):
        if "=" in item:
            k, v = item.split("=", 1)
            s.cookies.set(k, v, domain=".google.com")
            s.cookies.set(k, v, domain=".googleusercontent.com")
    return s

def clean_path(path_str):
    # Fix corrupt emoji sequences or trailing spaces
    parts = path_str.split("/")
    cleaned = []
    for p in parts:
        p = p.strip()
        p = p.replace("ðŸ“š", "📚").replace("âžª", "➔")
        cleaned.append(p)
    return "/".join(cleaned)

def download_one(session, file_info, base_dir="downloaded_files"):
    file_id = file_info["id"]
    rel_path = clean_path(file_info["path"])
    dest_path = os.path.join(base_dir, rel_path)

    # Check if already downloaded
    if os.path.exists(dest_path) and os.path.getsize(dest_path) > 1000:
        return {"status": "skipped", "path": rel_path, "size": os.path.getsize(dest_path)}

    url = f"https://drive.google.com/uc?id={file_id}&export=download"
    r = session.get(url, stream=True, timeout=60)

    # Handle virus warning page for large files
    if "text/html" in r.headers.get("content-type", ""):
        html = r.text
        # Check for form inputs
        inputs = re.findall(r'<input type="hidden" name="([^"]+)" value="([^"]+)"', html)
        if inputs:
            params = dict(inputs)
            action = "https://drive.usercontent.google.com/download"
            r = session.get(action, params=params, stream=True, timeout=120)
        else:
            # Check for confirm token
            m = re.search(r'confirm=([0-9A-Za-z_-]+)', html)
            if m:
                confirm = m.group(1)
                url = f"https://drive.google.com/uc?id={file_id}&export=download&confirm={confirm}"
                r = session.get(url, stream=True, timeout=120)

    folder = os.path.dirname(dest_path)
    if folder:
        os.makedirs(folder, exist_ok=True)

    temp_path = dest_path + ".tmp"
    with open(temp_path, "wb") as f:
        for chunk in r.iter_content(chunk_size=131072):
            if chunk:
                f.write(chunk)

    final_size = os.path.getsize(temp_path)
    if final_size == 0 or ("text/html" in r.headers.get("content-type", "") and final_size < 5000):
        # Likely an error page
        os.remove(temp_path)
        return {"status": "error", "path": rel_path, "error": "Empty or HTML error"}

    os.rename(temp_path, dest_path)
    return {"status": "downloaded", "path": rel_path, "size": final_size}

def main():
    with open("files_manifest.json") as f:
        files = json.load(f)

    print(f"Total files in manifest: {len(files)}")
    session = create_session()

    progress_file = "download_progress.json"
    downloaded_map = {}
    if os.path.exists(progress_file):
        try:
            with open(progress_file) as pf:
                downloaded_map = json.load(pf)
        except Exception:
            downloaded_map = {}

    total = len(files)
    count = 0
    errors = 0

    print("Starting download queue with 3 worker threads...")
    def worker(file_info):
        s = create_session()
        res = download_one(s, file_info)
        return file_info["id"], res

    with ThreadPoolExecutor(max_workers=3) as executor:
        futures = {executor.submit(worker, f): f for f in files}
        for future in as_completed(futures):
            count += 1
            f_info = futures[future]
            try:
                fid, res = future.result()
                status = res["status"]
                path = res["path"]
                if status == "downloaded":
                    mb = res.get("size", 0) / (1024 * 1024)
                    print(f"[{count}/{total}] [OK] {path} ({mb:.2f} MB)")
                    downloaded_map[fid] = res
                elif status == "skipped":
                    print(f"[{count}/{total}] [SKIP] {path} (already exists)")
                    downloaded_map[fid] = res
                else:
                    print(f"[{count}/{total}] [ERROR] {path}: {res.get('error')}")
                    errors += 1
            except Exception as e:
                print(f"[{count}/{total}] [EXCEPTION] {f_info['path']}: {e}")
                errors += 1

            if count % 20 == 0:
                with open(progress_file, "w") as pf:
                    json.dump(downloaded_map, pf, indent=2)

    with open(progress_file, "w") as pf:
        json.dump(downloaded_map, pf, indent=2)

    print(f"\nDownload finished! Processed: {count}, Errors: {errors}")

if __name__ == "__main__":
    main()
