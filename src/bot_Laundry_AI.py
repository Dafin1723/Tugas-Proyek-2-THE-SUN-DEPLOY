import logging
import sqlite3
import random
import os
from datetime import datetime
from dotenv import load_dotenv

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ReplyKeyboardMarkup,
    KeyboardButton
)

from telegram.ext import (
    Updater,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    Filters,
    CallbackContext
)

from groq import Groq

# ==============================
# CONFIG
# ==============================

load_dotenv()

TOKEN = os.getenv("TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
ADMIN_ID = 8028474070

if not TOKEN:
    raise ValueError("❌ TOKEN belum diset")

logging.basicConfig(
    format='%(asctime)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# ==============================
# DATABASE
# ==============================

conn = sqlite3.connect("laundry.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS orders(
id INTEGER PRIMARY KEY AUTOINCREMENT,
kode TEXT,
user_id INTEGER,
nama TEXT,
layanan TEXT,
alamat TEXT,
lat REAL,
lon REAL,
berat REAL,
harga INTEGER,
status TEXT,
tanggal TEXT
)
""")

conn.commit()

# ==============================
# UTIL
# ==============================

def ask_ai(text):
    if not GROQ_API_KEY:
        return "❌ AI tidak tersedia"

    if "sepatu" in text.lower() or "tas" in text.lower():
        return "Maaf, kami hanya melayani laundry pakaian ya 😊"
    
    try:
        client = Groq(api_key=GROQ_API_KEY)

        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {
                    "role": "system",
                    "content": """
Kamu adalah customer service laundry profesional.
TUGAS:
- Membantu pelanggan terkait layanan laundry
- Menjawab pertanyaan dengan jelas & singkat
- Mengarahkan user untuk melakukan order atau cek status

LAYANAN:
- Express (Rp9000/kg) → cepat
- Reguler (Rp6500/kg) → normal
- Setrika (Rp3000/kg)

ATURAN:
- HANYA bahas laundry pakaian
- Tolak sepatu, tas, dll
- Jangan jawab di luar topik laundry

GAYA:
- Santai tapi sopan
- Singkat (max 2-3 kalimat)
- Selalu arahkan ke aksi (order / cek status)

CONTOH:
User: "berapa harga laundry?"
Jawab:
"Kami ada 3 layanan:
Express Rp9000/kg, Reguler Rp6500/kg, dan Setrika Rp3000/kg 😊
Mau langsung order?"

User: "laundry sepatu bisa?"
Jawab:
"Maaf, kami hanya melayani laundry pakaian ya 😊
Silakan pilih layanan di menu untuk mulai order."

User: "berapa lama selesai?"
Jawab:
"Express lebih cepat dari reguler ya 😊
Mau pilih layanan sekarang?"


"""
                },
                {
                    "role": "user",
                    "content": text
                }
            ]
        )

        return response.choices[0].message.content

    except Exception as e:
        logging.error(e)
        return "❌ AI sedang error"

# ==============================
# KEYBOARD
# ==============================

def user_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🧺 Order Laundry", callback_data="order")],
        [InlineKeyboardButton("📦 Cek Status", callback_data="cek")],
        [InlineKeyboardButton("🤖 AI Laundry", callback_data="ai_menu")]
    ])

def admin_keyboard():
    return ReplyKeyboardMarkup([
        ["📊 Lihat Order"],
        ["🏠 Menu"]
    ], resize_keyboard=True)

# ==============================
# START
# ==============================

def start(update: Update, context: CallbackContext):

    update.message.reply_text(
        "👋 Selamat datang di Bot Laundry",
        reply_markup=user_menu()
    )

# ==============================
# ADMIN COMMAND
# ==============================

def admin_command(update: Update, context: CallbackContext):

    if update.message.from_user.id != ADMIN_ID:
        update.message.reply_text("❌ Bukan admin")
        return

    update.message.reply_text(
        "👑 ADMIN PANEL",
        reply_markup=admin_keyboard()
    )

# ==============================
# ORDER USER
# ==============================

def order(update: Update, context: CallbackContext):

    query = update.callback_query
    query.answer()

    keyboard = [
        [InlineKeyboardButton("⚡ Express(9000)", callback_data="express")],
        [InlineKeyboardButton("🧼 Reguler(6500)", callback_data="reguler")],
        [InlineKeyboardButton("👕 Setrika(3000)", callback_data="setrika")]
    ]

    query.message.reply_text(
        "Pilih layanan:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

def pilih_layanan(update: Update, context: CallbackContext):

    query = update.callback_query
    query.answer()

    context.user_data["layanan"] = query.data

    location_button = KeyboardButton(
        "📍 Kirim Lokasi",
        request_location=True
    )

    keyboard = ReplyKeyboardMarkup(
        [[location_button]],
        resize_keyboard=True
    )

    query.message.reply_text(
        "Kirim alamat atau lokasi:",
        reply_markup=keyboard
    )

# ==============================
# TERIMA LOKASI
# ==============================

def alamat_maps(update: Update, context: CallbackContext):

    if "layanan" not in context.user_data:
        return

    user = update.message.from_user
    layanan = context.user_data["layanan"]

    lat = update.message.location.latitude
    lon = update.message.location.longitude

    kode = generate_kode()

    link_maps = f"https://maps.google.com/?q={lat},{lon}"

    cursor.execute("""
    INSERT INTO orders(
    kode,user_id,nama,layanan,
    lat,lon,status,tanggal
    )
    VALUES(?,?,?,?,?,?,?,?)
    """, (
        kode,
        user.id,
        user.first_name,
        layanan,
        lat,
        lon,
        "🚚 Menunggu dijemput",
        datetime.now().strftime("%d-%m-%Y")
    ))

    conn.commit()

    update.message.reply_text(f"""
✅ ORDER BERHASIL

Kode: {kode}
