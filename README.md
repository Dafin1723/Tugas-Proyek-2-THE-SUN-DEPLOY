# THE SUN ☀️ — AI-Powered Laundry Bot

> Proyek 3 — AI Integration & Cloud Deployment  
> Kelompok THE SUN: Dafin, Iben, Fahad

---

## 📌 Deskripsi

Bot Telegram layanan laundry UMKM yang dilengkapi dengan kecerdasan buatan (Groq AI), sistem logging error otomatis, dan crash reporting ke admin.

---

## 🚀 Fitur

- 🧺 Order laundry (Express, Reguler, Setrika)
- 📍 Input alamat manual atau kirim lokasi maps
- 📦 Cek status pesanan via kode order
- 🤖 AI Customer Service (Groq LLM)
- 📝 Logging error otomatis ke `error_log.txt`
- 🚨 Notifikasi crash ke Telegram admin
- 👑 Panel admin (timbang, proses, antar, selesai)

---

## 🤖 Desain System Prompt AI

AI berperan sebagai **customer service laundry profesional** dengan ketentuan:

| Aspek | Keterangan |
|-------|------------|
| **Karakter** | Santai tapi sopan, singkat (maks 2-3 kalimat) |
| **Topik** | Hanya laundry pakaian, tolak sepatu/tas/dll |
| **Aksi** | Selalu arahkan ke order atau cek status |
| **Model** | `llama-3.3-70b-versatile` via Groq API |

---

## ⚙️ Instalasi Lokal

### 1. Clone Repository
```bash
git clone https://github.com/Dafin1723/Tugas-Proyek-2-THE-SUN-DEPLOY.git
cd Tugas-Proyek-2-THE-SUN-DEPLOY
```

### 2. Buat Virtual Environment
```bash
python -m venv venv
venv\Scripts\activate   # Windows
# atau
source venv/bin/activate  # Linux/Mac
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Konfigurasi Environment Variables

Salin file contoh lalu isi nilainya:
```bash
cp .env.example .env
```

Isi file `.env`:
```
TOKEN=token_bot_telegram_kamu
GROQ_API_KEY=api_key_groq_kamu
ADMIN_ID=chat_id_telegram_admin
```

> Cara dapat ADMIN_ID: kirim pesan ke @userinfobot di Telegram

### 5. Jalankan Bot
```bash
python src/main.py
```

---

## 🌐 Deployment (Railway)

1. Push kode ke GitHub (pastikan `.env` tidak ikut ter-push)
2. Buka [railway.app](https://railway.app) → New Project → Deploy from GitHub
3. Pilih repo ini
4. Masuk ke tab **Variables**, tambahkan:
   - `TOKEN`
   - `GROQ_API_KEY`
   - `ADMIN_ID`
5. Railway otomatis membaca `Procfile` dan menjalankan bot sebagai worker

---

## 📁 Struktur Project

```
Tugas-Proyek-2-THE-SUN-DEPLOY/
├── src/
│   └── main.py          ← Bot utama (AI + logging + crash reporting)
├── .env.example         ← Template environment variables
├── .gitignore           ← Proteksi file sensitif
├── Procfile             ← Konfigurasi Railway
├── requirements.txt     ← Daftar dependencies
└── README.md
```

---

🌞 **THE SUN** — Project 3 | © 2026 All Rights Reserved