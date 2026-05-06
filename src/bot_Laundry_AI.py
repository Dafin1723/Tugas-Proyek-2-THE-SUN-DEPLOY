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