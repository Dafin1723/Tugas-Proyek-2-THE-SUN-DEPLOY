import logging
import sqlite3
import random
from datetime import datetime

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

TOKEN = "TOKEN_BOT_TELEGRAM_KAMU"
GROQ_API_KEY = "GROQ_API_KEY"  # Ambil dari .env
ADMIN_ID = 8028474070

client = Groq(api_key=GROQ_API_KEY)

logging.basicConfig(level=logging.INFO)

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

def generate_kode():
    return f"LDR-{random.randint(10000,99999)}"

def ask_ai(text):

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {
                "role": "system",
                "content": """
Kamu adalah customer service laundry profesional.

ATURAN:
- Hanya jawab sesuai layanan berikut:
  - Express (Rp9000/kg)
  - Reguler (Rp6500/kg)
  - Setrika (Rp3000/kg)
- Tidak melayani sepatu, tas, dll
- Jika ditanya di luar layanan → tolak dengan sopan

GAYA:
- Santai tapi profesional
- Singkat
- Selalu arahkan ke aksi (order / cek status)

CONTOH:
User: "laundry sepatu bisa?"
Jawab:
"Maaf, saat ini kami hanya melayani laundry pakaian ya 😊
Silakan pilih layanan di menu untuk mulai order."
"""
            },
            {
                "role": "user",
                "content": text
            }
        ]
    )

    return response.choices[0].message.content

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