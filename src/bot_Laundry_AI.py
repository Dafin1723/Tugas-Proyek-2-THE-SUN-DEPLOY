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

    layanan, user_id = cursor.fetchone()

        if layanan == "express":
            harga = berat * 9000

        elif layanan == "reguler":
            harga = berat * 6500

        else:
            harga = berat * 3000

        cursor.execute("""
        UPDATE orders
        SET berat=?, harga=?, status=?
        WHERE kode=?
        """, (
            berat,
            harga,
            "⚖️ Ditimbang",
            kode
        ))

        conn.commit()

        context.bot.send_message(user_id, f"""
📦 Laundry ditimbang

Berat: {berat} kg
Total: Rp{int(harga)}
""")

        update.message.reply_text(
            "✅ Berhasil ditimbang",
            reply_markup=admin_keyboard()
        )

        context.user_data.clear()

        return

    # ==============================
    # INPUT KODE CEK
    # ==============================

    if context.user_data.get("cek"):

        cursor.execute("""
        SELECT kode,status,layanan,harga
        FROM orders
        WHERE kode=?
        """, (text,))

        data = cursor.fetchone()

        if not data:

            update.message.reply_text(
                "❌ Kode tidak ditemukan"
            )

            return

        kode, status, layanan, harga = data

        msg = f"""
📦 STATUS LAUNDRY

Kode: {kode}
Layanan: {layanan}
Status: {status}
"""

        if harga:
            msg += f"\nTotal: Rp{int(harga)}"

        update.message.reply_text(msg)

        context.user_data.clear()

        return

    # ==============================
    # INPUT ALAMAT MANUAL
    # ==============================

    if "layanan" in context.user_data:

        kode = generate_kode()

        cursor.execute("""
        INSERT INTO orders(
        kode,user_id,nama,layanan,
        alamat,status,tanggal
        )
        VALUES(?,?,?,?,?,?,?)
        """, (
            kode,
            user.id,
            user.first_name,
            context.user_data["layanan"],
            text,
            "🚚 Menunggu dijemput",
            datetime.now().strftime("%d-%m-%Y")
        ))

        conn.commit()

        update.message.reply_text(f"""
✅ ORDER BERHASIL

Kode: {kode}

📍 Alamat:
{text}
""")

        context.bot.send_message(ADMIN_ID, f"""
🔔 ORDER BARU

Kode: {kode}
Nama: {user.first_name}
Layanan: {context.user_data["layanan"]}

📍 Alamat:
{text}
""")

        context.user_data.clear()

        return

    # ==============================
    # AI CHAT
    # ==============================

    if context.user_data.get("ai"):

        try:

            jawab = ask_ai(text)

            update.message.reply_text(jawab)

        except Exception as e:

            print(e)

            update.message.reply_text("❌ AI error")
            return

# ==============================
# MAIN
# ==============================

def main():

    updater = Updater(TOKEN)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("admin", admin_command))

    dp.add_handler(
        CallbackQueryHandler(order, pattern="order")
    )s

    dp.add_handler(
        CallbackQueryHandler(
            pilih_layanan,
            pattern="express|reguler|setrika"
        )
    )

    dp.add_handler(
        CallbackQueryHandler(
            cek_status,
            pattern="cek"
        )
    )

    dp.add_handler(
        CallbackQueryHandler(
            ai_panel,
            pattern="ai_menu"
        )
    )

    dp.add_handler(
        CallbackQueryHandler(
            ai_on,
            pattern="ai_on"
        )
    )

    dp.add_handler(
        CallbackQueryHandler(
            ai_off,
            pattern="ai_off"
        )
    )

    dp.add_handler(
        CallbackQueryHandler(
            pilih_order,
            pattern="pilih_"
        )
    )

    dp.add_handler(
        CallbackQueryHandler(
            aksi_admin,
            pattern="aksi_|kembali"
        )
    )

    dp.add_handler(
        MessageHandler(
            Filters.location,
            alamat_maps
        )
    )

    dp.add_handler(
        MessageHandler(
            Filters.text & ~Filters.command,
            handle_text
        )
    )

    updater.start_polling()
    print("BOT RUNNING...")
    updater.idle()

if __name__ == "__main__":
    main()