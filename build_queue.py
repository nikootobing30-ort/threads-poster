"""Masukkan paket konten mingguan ke antrean posting Threads.

Usage: python build_queue.py <folder-paket>
  <folder-paket> berisi antrean.json (dibuat skill affiliate-konten) dan folder kartu\\ (PNG).

Format antrean.json paket:
{"posts": [{"id": "2026-11-23-0700", "scheduled_at": "2026-11-23T07:00:00+07:00",
            "type": "tanpa_link", "topic": "Tips Dapur", "text": "...", "image": "kartu/01-cover.png" | null,
            "reply_text": "... https://s.shopee.co.id/xxxx (link affiliate)" | null}]}
"""
import datetime as dt
import json
import pathlib
import shutil
import sys

ROOT = pathlib.Path(__file__).resolve().parent
QUEUE = ROOT / "antrean" / "queue.json"
MAX_CHARS = 500
DEFAULT_TOPIC = "Racun Shopee"


def fail(msg):
    sys.exit(f"GAGAL: {msg}")


def threads_length(text):
    """Threads menghitung emoji sebagai jumlah byte UTF-8-nya.
    Perkiraan aman: karakter di luar teks biasa (>= U+2000) dihitung per byte UTF-8."""
    return sum(len(c.encode("utf-8")) if ord(c) >= 0x2000 else 1 for c in text)


def check_topic(topic, pid):
    if not 1 <= len(topic) <= 50 or "." in topic or "&" in topic:
        fail(f"{pid}: topik '{topic}' tidak valid (1–50 karakter, tanpa titik dan &)")


def main():
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    pkg = pathlib.Path(sys.argv[1]).resolve()
    data = json.loads((pkg / "antrean.json").read_text(encoding="utf-8-sig"))
    queue = json.loads(QUEUE.read_text(encoding="utf-8-sig")) if QUEUE.exists() else {"posts": []}
    existing = {p["id"] for p in queue["posts"]}
    img_dir = ROOT / "images" / pkg.name
    added = 0

    for p in data["posts"]:
        for key in ("id", "scheduled_at", "text"):
            if not p.get(key):
                fail(f"postingan tanpa '{key}': {p}")
        dt.datetime.fromisoformat(p["scheduled_at"])  # validasi format
        if "+" not in p["scheduled_at"][10:]:
            fail(f"{p['id']}: scheduled_at harus ada zona waktu, mis. +07:00")
        for key in ("text", "reply_text"):
            if p.get(key) and threads_length(p[key]) > MAX_CHARS:
                fail(f"{p['id']}: {key} {threads_length(p[key])} karakter versi Threads (> {MAX_CHARS})")
        topic = (p.get("topic") or DEFAULT_TOPIC).strip()
        check_topic(topic, p["id"])
        if p["id"] in existing:
            print(f"lewati {p['id']} (sudah ada di antrean)")
            continue
        item = {k: p.get(k) for k in ("id", "scheduled_at", "type", "text", "reply_text")}
        item["topic"] = topic
        if p.get("image"):
            src = pkg / p["image"]
            if not src.exists():
                fail(f"{p['id']}: gambar tidak ada: {src}")
            img_dir.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, img_dir / src.name)
            item["image"] = f"images/{pkg.name}/{src.name}"
        item["status"] = "pending"
        queue["posts"].append(item)
        added += 1

    queue["posts"].sort(key=lambda x: x["scheduled_at"])
    QUEUE.parent.mkdir(parents=True, exist_ok=True)
    QUEUE.write_text(json.dumps(queue, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    pending = sum(1 for p in queue["posts"] if p.get("status") == "pending")
    print(f"Ditambahkan {added} postingan. Total menunggu: {pending}.")


if __name__ == "__main__":
    main()
