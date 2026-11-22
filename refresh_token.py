"""Perpanjang token Threads (berlaku 60 hari) dan cetak token baru ke stdout.

Dipakai workflow perpanjang-token.yml yang langsung menyimpannya ke GitHub Secret.
Jangan jalankan lalu menyalin hasilnya ke chat — token bersifat rahasia.
"""
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request

token = os.environ.get("THREADS_TOKEN")
if not token:
    sys.exit("THREADS_TOKEN tidak ada")
q = urllib.parse.urlencode({"grant_type": "th_refresh_token", "access_token": token})
try:
    with urllib.request.urlopen(f"https://graph.threads.net/refresh_access_token?{q}", timeout=60) as r:
        data = json.load(r)
except urllib.error.HTTPError as e:
    sys.exit(f"Gagal memperpanjang token ({e.code}): {e.read().decode(errors='replace')[:300]}")
new = data.get("access_token")
if not new:
    sys.exit("Respons tidak berisi access_token")
days = int(data.get("expires_in", 0)) // 86400
print(f"Token diperpanjang, berlaku {days} hari.", file=sys.stderr)
print(new)
