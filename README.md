# Agen Posting Threads — @dapurhematid

Memposting antrean konten affiliate ke Threads 3x sehari (07.05, 12.05, 19.05 WIB) lewat
GitHub Actions — laptop boleh mati. Gratis (Threads API tidak berbayar).

## Isi folder

| File | Fungsi |
|---|---|
| `poster.py` | Posting item antrean yang sudah jatuh tempo (teks/gambar + balasan berisi link) |
| `build_queue.py` | Memasukkan paket mingguan dari skill `affiliate-konten` ke antrean |
| `refresh_token.py` | Memperpanjang token 60 hari |
| `antrean/queue.json` | Antrean + status tiap postingan (`pending`, `posted`, `skipped`, `failed`) |
| `images/` | Gambar kartu (harus publik agar bisa diambil Threads) |
| `.github/workflows/posting.yml` | Jadwal posting |
| `.github/workflows/perpanjang-token.yml` | Perpanjang token tiap Senin |

## Penyiapan (sekali)

1. **Repo GitHub publik** bernama `threads-poster` (publik agar gambar bisa dibaca Threads;
   tidak ada rahasia di repo — token disimpan di Secrets).
2. **Token Threads**: Meta for Developers → aplikasi *Dapur Hemat Poster* → Use cases →
   Access the Threads API → Customize → Settings → *User Token Generator* → Generate token untuk
   `dapurhematid`. Salin token itu **langsung** ke langkah 3 (jangan kirim ke chat/orang lain).
3. Repo GitHub → Settings → Secrets and variables → Actions → **New repository secret**:
   - `THREADS_TOKEN` = token dari langkah 2
   - `GH_PAT` = *fine-grained personal access token* GitHub dengan akses hanya ke repo ini,
     izin **Secrets: Read and write** (agar token bisa diperpanjang otomatis). Opsional tetapi
     disarankan; tanpa ini token harus dibuat ulang manual tiap < 60 hari.
4. Repo → Actions → aktifkan workflow → jalankan **Perpanjang token Threads** sekali secara manual
   (setelah token berumur ≥ 24 jam) untuk menguji.

## Cara kerja mingguan

Tugas mingguan Claude di laptop membuat paket konten, lalu:

```
python build_queue.py C:\insentif\konten\<tanggal>-mingguan
git add -A && git commit -m "antrean minggu <tanggal>" && git push
```

## Uji lokal tanpa memposting

```
$env:DRY_RUN = "1"; python poster.py
```
