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
Layanan: {layanan}

📍 {link_maps}
""")

    context.bot.send_message(ADMIN_ID, f"""
🔔 ORDER BARU

Kode: {kode}
Nama: {user.first_name}
Layanan: {layanan}

📍 {link_maps}
""")

    context.user_data.clear()

# ==============================
# ADMIN SYSTEM
# ==============================

def list_order(update: Update, context: CallbackContext):

    cursor.execute("""
    SELECT kode,nama,status
    FROM orders
    ORDER BY id DESC
    LIMIT 10
    """)

    data = cursor.fetchall()

    if not data:
        update.message.reply_text("Belum ada order")
        return

    keyboard = [
        [
            InlineKeyboardButton(
                f"{d[0]} - {d[1]} ({d[2]})",
                callback_data=f"pilih_{d[0]}"
            )
        ]
        for d in data
    ]

    update.message.reply_text(
        "📊 Pilih Order:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

def pilih_order(update: Update, context: CallbackContext):

    query = update.callback_query
    query.answer()

    kode = query.data.replace("pilih_", "")

    context.user_data["kode"] = kode

    keyboard = [
        [InlineKeyboardButton("⚖️ Timbang", callback_data="aksi_timbang")],
        [InlineKeyboardButton("🧼 Proses", callback_data="aksi_proses")],
        [InlineKeyboardButton("🚀 Antar", callback_data="aksi_antar")],
        [InlineKeyboardButton("✅ Selesai", callback_data="aksi_selesai")],
        [InlineKeyboardButton("🔙 Kembali", callback_data="kembali")]
    ]

    query.message.reply_text(
        f"📦 Order: {kode}",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

def aksi_admin(update: Update, context: CallbackContext):

    query = update.callback_query
    query.answer()

    data = query.data

    if data == "kembali":
        list_order(query, context)
        return

    kode = context.user_data.get("kode")

    if not kode:
        query.message.reply_text("❌ Tidak ada kode")
        return

    if data == "aksi_timbang":

        context.user_data["berat"] = True

        query.message.reply_text(
            "Masukkan berat laundry (kg)"
        )

        return

    status_map = {
        "aksi_proses": "🧼 Diproses",
        "aksi_antar": "🚀 Diantar",
        "aksi_selesai": "✅ Selesai"
    }

    status = status_map[data]

    cursor.execute(
        "SELECT user_id FROM orders WHERE kode=?",
        (kode,)
    )

    user_id = cursor.fetchone()[0]

    cursor.execute("""
    UPDATE orders
    SET status=?
    WHERE kode=?
    """, (status, kode))

    conn.commit()

    context.bot.send_message(user_id, f"""
📦 UPDATE LAUNDRY

Kode: {kode}
Status: {status}
""")

    query.message.reply_text("✅ Status berhasil diupdate")

# ==============================
# AI SYSTEM
# ==============================

def ai_panel(update: Update, context: CallbackContext):

    query = update.callback_query
    query.answer()

    keyboard = [
        [InlineKeyboardButton("🟢 Aktifkan AI", callback_data="ai_on")],
        [InlineKeyboardButton("🔴 Matikan AI", callback_data="ai_off")]
    ]

    query.message.reply_text(
        "🤖 AI Laundry",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

def ai_on(update: Update, context: CallbackContext):

    query = update.callback_query
    query.answer()

    context.user_data["ai"] = True

    query.message.reply_text(
        "🤖 AI aktif\nSilakan chat soal laundry"
    )

def ai_off(update: Update, context: CallbackContext):

    query = update.callback_query
    query.answer()

    context.user_data["ai"] = False

    query.message.reply_text("❌ AI dimatikan")

# ==============================
# CEK STATUS USER
# ==============================

def cek_status(update: Update, context: CallbackContext):

    query = update.callback_query
    query.answer()

    context.user_data["cek"] = True

    query.message.reply_text(
        "Masukkan kode order"
    )

# ==============================
# HANDLE TEXT
# ==============================

def handle_text(update: Update, context: CallbackContext):

    text = update.message.text
    user = update.message.from_user

    # ==============================
    # ADMIN MENU
    # ==============================

    if text == "📊 Lihat Order":
        list_order(update, context)
        return

    if text == "🏠 Menu":

        context.user_data.clear()

        update.message.reply_text(
            "🏠 Menu utama",
            reply_markup=user_menu()
        )

        return

    # ==============================
    # INPUT BERAT
    # ==============================

    if "berat" in context.user_data:

        try:
            berat = float(text.replace(",", "."))

        except:
            update.message.reply_text(
                "❌ Masukkan angka"
            )
            return

        kode = context.user_data["kode"]

        cursor.execute("""
        SELECT layanan,user_id
        FROM orders
        WHERE kode=?
        """, (kode,))
