import requests
import re
import os

COOKIE = """COMPASS=drive=CgAQz82o1wYauQEACWuJV-eznuhGsHSV6P6wiJ49ncDLhMC5eNDQ7XfyfC0e4qXZGMB8IrxVa51JL4FjVB21y5z9PAqJYDBD-g4TEVrvG4WtxMeooMEcK2DvGqORRbDlH2yhTD55nYIcif1s1CyqeKc9_5ymuDFnsezAieeVnSbfslj3edSJH941IS_ru2s6T20hju-CThjrnA9c0vnk9498VD5ztO8-eBzhxF8EBg42Ws3OTzKUr7hmvdLUB1Co3b1bnzAB; HSID=AVyWlRqIF5kC_5_Wj; SSID=An0jexAMbFSnd0MwD; APISID=D00EXtKOuAG1OFB9/AT5RDekKMRu8NkfLD; SAPISID=DDlOF2Yd-g7Cdide/AUGgbKpei4bux2sep; __Secure-1PAPISID=DDlOF2Yd-g7Cdide/AUGgbKpei4bux2sep; __Secure-3PAPISID=DDlOF2Yd-g7Cdide/AUGgbKpei4bux2sep; SEARCH_SAMESITE=CgQI-qEB; OSID=g.a000EAnJGAyYEt20cRPJNcHOlZJWCTn3o8MYVMff2fVskkGZaLkbZPo0eA42WMUmN7AkAEy1QQACgYKATMSARMSFQHGX2MiM0vNpVDsxLMjR-IXKu3C1hoVAUF8yKrwvPq-2b55uc5U8MKM0Rgi0076; __Secure-OSID=g.a000EAnJGAyYEt20cRPJNcHOlZJWCTn3o8MYVMff2fVskkGZaLkbvg1RTz3eBO2x9i5WcZh9YAACgYKAfISARMSFQHGX2MiYwj4V_AkqKuY1vcrcLMYqhoVAUF8yKqPUcAA5UFoM86umuQpYiB-0076; SID=g.a000EQnJGAKTVvU2ZSlIPDm5eFNikgSnagM7oAPXBt7cyiPy7BBbYcAmSxytXe0_2yT7aXo78gACgYKAccSARMSFQHGX2MiHHGkGdlojGKUyH2NrAwS-hoVAUF8yKpxWR-ad6HVm6sUZ3UBISUy0076; __Secure-1PSID=g.a000EQnJGAKTVvU2ZSlIPDm5eFNikgSnagM7oAPXBt7cyiPy7BBbR7TqOTu8s94B9PmtMbvM5QACgYKAZUSARMSFQHGX2Mi4QTYub8fx_QAFZ6q2JsccxoVAUF8yKqUNl7Q3jSplwRQ3_3JheQs0076; __Secure-3PSID=g.a000EQnJGAKTVvU2ZSlIPDm5eFNikgSnagM7oAPXBt7cyiPy7BBbZdSEmZ4BuAtiJZHlVeB-7gACgYKAXESARMSFQHGX2MivADFvKTg62kK1GKwcmuTpBoVAUF8yKq--KQgD3m2MbTU4oCath3M0076; GCL_AW_P=GCL.1793624557.CjwKCAjwxrLHBhA2EiwAu9EdM8KRuXEni6idmvbbr0G7S_IUda_WByaWQ2aabNuzPt0y0MDkA5F1IRoC53IQAvD_BwE; AEC=Aaa9EJrHfQeqpWJUn_RP0sSKSFNqqZ-CLsnKbz1btf-0ejtykF3LS5cpZD0; NID=CsADCAES8gIBM9Agl7h7U897SGuXJjv5CF7q90q8c3tmAtS0KP2QBcfupN1EJsjIdsfpC3ZrpH681Ha95aap4IlTgd206GY89x86XlfeoJ_uYGgO2lLf7SnYgilEOyc_uS1qpuWgiqSG4LUyt_SBVauQZeznF750nOHAD_YxgmqA7NGKLdNEyahE1TiLq3r2E5RCBErbWEBnQbT2fA1yeC5HIsf6tz7e0zWqxZxBprHvk0YxzxjZimbUjlxoNBiTaNHiQz_zhLY2mYE1MNnZZOosgywUQRCv8IHjGeGrP2ECys1z65VTOIq64rWYoHhJ9CZI9LMhPq03syRm8hqLFXUT5bHC-Nwagjb7VGtGnSAqpxow9j8BSkCgzQ4v2On-IUbCKxFMiqIMB6RvBZRV6ieENvupMKQ4aDFKHgvnjrCbM_OIxwMyDD4Hc1neisNVjCPInrh_RwE8rjC5jKhj6uVy_1PA4ykCFaLNV9GM2HLfSPQRX2vyHwfoKAEyRQFwSkLPOZa2TESMklusnlngQpkxvDwEEw3lwumTIXHn6UxRmtH7ZXN31gY0O0VW4JmYJJbc9XX4UfMX2jaxYIulOTMWBw; OTZ=8857034_34_34__34_; COMPASS=appsfrontendserver=CgAQ2M2o1wYagwEACWuJVwzi4WUYkrRbTB-TRu1gXWauEw0h_wi6kakpJ3Z5G0OB1WIZ3FQjjDqoqQQyD83EUmlsMKKwXvNURjgXFOhKfjABCdI_wuCaxw-SNWrTyf4W8_rcDWCDtaLFF7GuLGB9ScJxaU3-hN4nMYCN1Un1JDubcknez09PsGVKGCJpMyABMAE; __Secure-1PSIDTS=sidts-CjIBnJZzakvF-5oPiFJIY1htS2nGEcFrlyWo_r8u6r8JZKe6cimo-apnYkCqOjMdBh6xfhAA; __Secure-3PSIDTS=sidts-CjIBnJZzakvF-5oPiFJIY1htS2nGEcFrlyWo_r8u6r8JZKe6cimo-apnYkCqOjMdBh6xfhAA; SIDCC=APD_SKGvD0Y5qEkKh0JSItrWej_y3Jj91c_HIvBBpFVumIGVQvNklCO0jJWcAYspHPHtom6sw0s; __Secure-1PSIDCC=APD_SKE0V9gP6Qeb216x0E8Hkurbmh0PuWnk__5xgwPiaiNgcXC30Y_ZVcHtt2_l9d0P1mtvG4M; __Secure-3PSIDCC=APD_SKH2kylWUza7jLuQK-_DZEEEJaiQYwTCi7lLiOvltydInVCg7L1KgrntkA3RE1lzEcXpGxUH""".strip()

s = requests.Session()
s.headers.update({
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Cookie": COOKIE
})

def download_file(file_id, dest_path):
    url = f"https://drive.google.com/uc?id={file_id}&export=download"
    r = s.get(url, stream=True)
    
    ctype = r.headers.get("content-type", "")
    if "text/html" in ctype:
        text = r.text
        m = re.search(r"confirm=([0-9A-Za-z_]+)", text)
        if m:
            confirm = m.group(1)
            url = f"https://drive.google.com/uc?id={file_id}&export=download&confirm={confirm}"
            r = s.get(url, stream=True)
        elif "drive.usercontent.google.com/download" in text:
            m = re.search(r'href="([^"]+download[^"]+)"', text)
            if m:
                url = m.group(1).replace("&amp;", "&")
                r = s.get(url, stream=True)

    folder = os.path.dirname(dest_path)
    if folder:
        os.makedirs(folder, exist_ok=True)
        
    with open(dest_path, "wb") as f:
        for chunk in r.iter_content(chunk_size=65536):
            if chunk:
                f.write(chunk)
    size = os.path.getsize(dest_path)
    print(f"Downloaded {dest_path}, size={size} bytes, content-type={r.headers.get('content-type')}")

download_file("1XflI-BofoW3i5rJyDhfNliRkv_cuH2W-", "test_file.pdf")
