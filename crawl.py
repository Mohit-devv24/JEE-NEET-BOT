import requests
import json
import re
import os

COOKIE = """COMPASS=drive=CgAQz82o1wYauQEACWuJV-eznuhGsHSV6P6wiJ49ncDLhMC5eNDQ7XfyfC0e4qXZGMB8IrxVa51JL4FjVB21y5z9PAqJYDBD-g4TEVrvG4WtxMeooMEcK2DvGqORRbDlH2yhTD55nYIcif1s1CyqeKc9_5ymuDFnsezAieeVnSbfslj3edSJH941IS_ru2s6T20hju-CThjrnA9c0vnk9498VD5ztO8-eBzhxF8EBg42Ws3OTzKUr7hmvdLUB1Co3b1bnzAB; HSID=AVyWlRqIF5kC_5_Wj; SSID=An0jexAMbFSnd0MwD; APISID=D00EXtKOuAG1OFB9/AT5RDekKMRu8NkfLD; SAPISID=DDlOF2Yd-g7Cdide/AUGgbKpei4bux2sep; __Secure-1PAPISID=DDlOF2Yd-g7Cdide/AUGgbKpei4bux2sep; __Secure-3PAPISID=DDlOF2Yd-g7Cdide/AUGgbKpei4bux2sep; SEARCH_SAMESITE=CgQI-qEB; OSID=g.a000EAnJGAyYEt20cRPJNcHOlZJWCTn3o8MYVMff2fVskkGZaLkbZPo0eA42WMUmN7AkAEy1QQACgYKATMSARMSFQHGX2MiM0vNpVDsxLMjR-IXKu3C1hoVAUF8yKrwvPq-2b55uc5U8MKM0Rgi0076; __Secure-OSID=g.a000EAnJGAyYEt20cRPJNcHOlZJWCTn3o8MYVMff2fVskkGZaLkbvg1RTz3eBO2x9i5WcZh9YAACgYKAfISARMSFQHGX2MiYwj4V_AkqKuY1vcrcLMYqhoVAUF8yKqPUcAA5UFoM86umuQpYiB-0076; SID=g.a000EQnJGAKTVvU2ZSlIPDm5eFNikgSnagM7oAPXBt7cyiPy7BBbYcAmSxytXe0_2yT7aXo78gACgYKAccSARMSFQHGX2MiHHGkGdlojGKUyH2NrAwS-hoVAUF8yKpxWR-ad6HVm6sUZ3UBISUy0076; __Secure-1PSID=g.a000EQnJGAKTVvU2ZSlIPDm5eFNikgSnagM7oAPXBt7cyiPy7BBbR7TqOTu8s94B9PmtMbvM5QACgYKAZUSARMSFQHGX2Mi4QTYub8fx_QAFZ6q2JsccxoVAUF8yKqUNl7Q3jSplwRQ3_3JheQs0076; __Secure-3PSID=g.a000EQnJGAKTVvU2ZSlIPDm5eFNikgSnagM7oAPXBt7cyiPy7BBbZdSEmZ4BuAtiJZHlVeB-7gACgYKAXESARMSFQHGX2MivADFvKTg62kK1GKwcmuTpBoVAUF8yKq--KQgD3m2MbTU4oCath3M0076; GCL_AW_P=GCL.1793624557.CjwKCAjwxrLHBhA2EiwAu9EdM8KRuXEni6idmvbbr0G7S_IUda_WByaWQ2aabNuzPt0y0MDkA5F1IRoC53IQAvD_BwE; AEC=Aaa9EJrHfQeqpWJUn_RP0sSKSFNqqZ-CLsnKbz1btf-0ejtykF3LS5cpZD0; NID=CsADCAES8gIBM9Agl7h7U897SGuXJjv5CF7q90q8c3tmAtS0KP2QBcfupN1EJsjIdsfpC3ZrpH681Ha95aap4IlTgd206GY89x86XlfeoJ_uYGgO2lLf7SnYgilEOyc_uS1qpuWgiqSG4LUyt_SBVauQZeznF750nOHAD_YxgmqA7NGKLdNEyahE1TiLq3r2E5RCBErbWEBnQbT2fA1yeC5HIsf6tz7e0zWqxZxBprHvk0YxzxjZimbUjlxoNBiTaNHiQz_zhLY2mYE1MNnZZOosgywUQRCv8IHjGeGrP2ECys1z65VTOIq64rWYoHhJ9CZI9LMhPq03syRm8hqLFXUT5bHC-Nwagjb7VGtGnSAqpxow9j8BSkCgzQ4v2On-IUbCKxFMiqIMB6RvBZRV6ieENvupMKQ4aDFKHgvnjrCbM_OIxwMyDD4Hc1neisNVjCPInrh_RwE8rjC5jKhj6uVy_1PA4ykCFaLNV9GM2HLfSPQRX2vyHwfoKAEyRQFwSkLPOZa2TESMklusnlngQpkxvDwEEw3lwumTIXHn6UxRmtH7ZXN31gY0O0VW4JmYJJbc9XX4UfMX2jaxYIulOTMWBw; OTZ=8857034_34_34__34_; COMPASS=appsfrontendserver=CgAQ2M2o1wYagwEACWuJVwzi4WUYkrRbTB-TRu1gXWauEw0h_wi6kakpJ3Z5G0OB1WIZ3FQjjDqoqQQyD83EUmlsMKKwXvNURjgXFOhKfjABCdI_wuCaxw-SNWrTyf4W8_rcDWCDtaLFF7GuLGB9ScJxaU3-hN4nMYCN1Un1JDubcknez09PsGVKGCJpMyABMAE; __Secure-1PSIDTS=sidts-CjIBnJZzakvF-5oPiFJIY1htS2nGEcFrlyWo_r8u6r8JZKe6cimo-apnYkCqOjMdBh6xfhAA; __Secure-3PSIDTS=sidts-CjIBnJZzakvF-5oPiFJIY1htS2nGEcFrlyWo_r8u6r8JZKe6cimo-apnYkCqOjMdBh6xfhAA; SIDCC=APD_SKGvD0Y5qEkKh0JSItrWej_y3Jj91c_HIvBBpFVumIGVQvNklCO0jJWcAYspHPHtom6sw0s; __Secure-1PSIDCC=APD_SKE0V9gP6Qeb216x0E8Hkurbmh0PuWnk__5xgwPiaiNgcXC30Y_ZVcHtt2_l9d0P1mtvG4M; __Secure-3PSIDCC=APD_SKH2kylWUza7jLuQK-_DZEEEJaiQYwTCi7lLiOvltydInVCg7L1KgrntkA3RE1lzEcXpGxUH""".strip()

s = requests.Session()
s.headers.update({
    "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 18_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.5 Mobile/15E148 Safari/604.1",
    "Cookie": COOKIE
})

def get_folder_items(folder_id):
    url = f"https://drive.google.com/drive/mobile/folders/{folder_id}"
    r = s.get(url)
    m = re.search(r"window\[\x27_DRIVE_ivd\x27\]\s*=\s*\x27(.*?)\x27;", r.text)
    if not m:
        m = re.search(r"window\[\"_DRIVE_ivd\"\]\s*=\s*\"(.*?)\";", r.text)
    if not m:
        print(f"Could not find _DRIVE_ivd for {folder_id}, status={r.status_code}")
        return []
    raw_escaped = m.group(1)
    raw_str = raw_escaped.encode("utf-8").decode("unicode_escape")
    data = json.loads(raw_str)
    items = []
    if not data or not data[0]:
        return []
    for item in data[0]:
        item_id = item[0]
        name = item[2]
        mime = item[3]
        is_folder = (mime == "application/vnd.google-apps.folder")
        size = item[4] if len(item) > 4 else None
        items.append({
            "id": item_id,
            "name": name,
            "mime": mime,
            "is_folder": is_folder,
            "size": size
        })
    return items

def crawl(folder_id, current_path=""):
    items = get_folder_items(folder_id)
    all_files = []
    for it in sorted(items, key=lambda x: x["name"]):
        rel_path = os.path.join(current_path, it["name"])
        if it["is_folder"]:
            print(f"[Folder] {rel_path} (ID: {it['id']})")
            sub_files = crawl(it["id"], rel_path)
            all_files.extend(sub_files)
        else:
            print(f" [File]  {rel_path} (ID: {it['id']})")
            it["path"] = rel_path
            all_files.append(it)
    return all_files

if __name__ == "__main__":
    root_id = "1V3GtPtz0YFBndpbs6j7Hq1c8g2aes99Z"
    print("Crawling root folder:", root_id)
    files = crawl(root_id)
    print("\nTotal files found:", len(files))
    with open("files_manifest.json", "w") as f:
        json.dump(files, f, indent=2)
    print("Saved files_manifest.json")
