"""Agen Posting Threads — memposting antrean yang sudah jatuh tempo.

Dijalankan oleh GitHub Actions 3x sehari (lihat .github/workflows/posting.yml).
Hanya memakai pustaka standar Python (tanpa pip install).

Variabel lingkungan:
  THREADS_TOKEN     token akses Threads (GitHub Secret) — wajib kecuali DRY_RUN=1
  IMAGE_BASE_URL    URL publik folder repo, mis. https://raw.githubusercontent.com/<user>/<repo>/main/
  DRY_RUN=1         hanya tampilkan apa yang akan diposting, tidak memanggil API, tidak mengubah antrean
  MAX_PER_RUN       maks. postingan per jalan (default 2)
  LATE_LIMIT_HOURS  postingan yang terlambat lebih dari ini dilewati (default 8)
"""
import datetime as dt
import json
import os
import pathlib
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

API = "https://graph.threads.net/v1.0"
ROOT = pathlib.Path(__file__).resolve().parent
QUEUE = ROOT / "antrean" / "queue.json"
WIB = dt.timezone(dt.timedelta(hours=7))
DRY = os.getenv("DRY_RUN") == "1"
MAX_PER_RUN = int(os.getenv("MAX_PER_RUN", "2"))
LATE_LIMIT_H = float(os.getenv("LATE_LIMIT_HOURS", "8"))
MAX_ATTEMPTS = 3


def call(method, path, params):
    """Panggil Threads API. Token tidak pernah dicetak."""
    params = {**params, "access_token": os.environ["THREADS_TOKEN"]}
    body = urllib.parse.urlencode(params)
    url = f"{API}/{path}"
    if method == "GET":
        req = urllib.request.Request(f"{url}?{body}")
    else:
        req = urllib.request.Request(url, data=body.encode(), method="POST")
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        detail = e.read().decode(errors="replace")[:500]
        raise RuntimeError(f"{method} {path} gagal ({e.code}): {detail}") from None


def wait_ready(container_id):
    for _ in range(20):
        info = call("GET", container_id, {"fields": "status,error_message"})
        status = info.get("status")
        if status == "FINISHED":
            return
        if status in ("ERROR", "EXPIRED"):
            raise RuntimeError(f"container {status}: {info.get('error_message')}")
        time.sleep(3)
    raise RuntimeError("container tidak siap setelah 60 detik")


def publish(text, image_url=None, reply_to=None, topic=None):
    params = {"text": text, "media_type": "IMAGE" if image_url else "TEXT"}
    if image_url:
        params["image_url"] = image_url
    if reply_to:
        params["reply_to_id"] = reply_to
    if topic:
        params["topic_tag"] = topic
    try:
        container = call("POST", "me/threads", params)["id"]
    except RuntimeError as e:
        if not topic:
            raise
        # Jika topik ditolak, posting tetap jalan tanpa topik.
        print(f"  topik '{topic}' ditolak, ulang tanpa topik: {str(e)[:150]}", file=sys.stderr)
        params.pop("topic_tag")
        container = call("POST", "me/threads", params)["id"]
    wait_ready(container)
    return call("POST", "me/threads_publish", {"creation_id": container})["id"]


def image_url_for(item):
    if not item.get("image"):
        return None
    base = os.getenv("IMAGE_BASE_URL", "")
    if not base:
        raise RuntimeError("IMAGE_BASE_URL belum diatur, padahal postingan memakai gambar")
    return base.rstrip("/") + "/" + item["image"].lstrip("/")


def save(queue):
    QUEUE.write_text(json.dumps(queue, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main():
    if not DRY and not os.getenv("THREADS_TOKEN"):
        sys.exit("THREADS_TOKEN tidak ada. Simpan token di GitHub Secrets dengan nama THREADS_TOKEN.")
    queue = json.loads(QUEUE.read_text(encoding="utf-8-sig"))
    now = dt.datetime.now(WIB)
    posted, errors = 0, 0

    for item in sorted(queue.get("posts", []), key=lambda x: x["scheduled_at"]):
        status = item.get("status", "pending")
        if status in ("posted", "skipped", "failed"):
            continue
        due = dt.datetime.fromisoformat(item["scheduled_at"])
        if due > now:
            continue
        if not item.get("post_id") and (now - due).total_seconds() > LATE_LIMIT_H * 3600:
            item["status"], item["note"] = "skipped", "terlambat lebih dari batas"
            continue
        if posted >= MAX_PER_RUN:
            break

        label = f"[{item['id']}] {item['scheduled_at']}"
        if DRY:
            print(f"DRY {label}\n  teks ({len(item['text'])}): {item['text'][:120]}…")
            if item.get("topic"):
                print(f"  topik: {item['topic']}")
            if item.get("image"):
                print(f"  gambar: {image_url_for(item) if os.getenv('IMAGE_BASE_URL') else item['image']}")
            if item.get("reply_text"):
                print(f"  balasan ({len(item['reply_text'])}): {item['reply_text'][:120]}…")
            posted += 1
            continue

        try:
            if not item.get("post_id"):
                item["post_id"] = publish(item["text"], image_url_for(item), topic=item.get("topic"))
                print(f"OK  {label} -> post {item['post_id']}")
            if item.get("reply_text") and not item.get("reply_id"):
                time.sleep(5)
                item["reply_id"] = publish(item["reply_text"], reply_to=item["post_id"])
                print(f"OK  {label} -> balasan {item['reply_id']}")
            item["status"] = "posted"
            item["posted_at"] = dt.datetime.now(WIB).isoformat(timespec="seconds")
            item.pop("error", None)
            posted += 1
        except Exception as e:  # catat lalu lanjut; dicoba lagi di jalan berikutnya
            errors += 1
            item["attempts"] = item.get("attempts", 0) + 1
            item["error"] = str(e)[:300]
            if item["attempts"] >= MAX_ATTEMPTS:
                item["status"] = "failed"
            print(f"ERR {label}: {item['error']}", file=sys.stderr)
        save(queue)

    if not DRY:
        save(queue)
    print(f"Selesai: {posted} diposting, {errors} gagal.")
    sys.exit(1 if errors else 0)


if __name__ == "__main__":
    main()
