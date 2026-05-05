# ==============================
# START
# ==============================

def start(update: Update, context: CallbackContext):
    update.message.reply_text(
        "👋 Selamat datang di Bot Laundry",
        reply_markup=user_menu()
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
# AI SYSTEM + CEK
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
    context.user_data["ai"] = True
    update.callback_query.message.reply_text("AI aktif")

def ai_off(update: Update, context: CallbackContext):
    context.user_data["ai"] = False
    update.callback_query.message.reply_text("AI mati")

def cek_status(update: Update, context: CallbackContext):
    context.user_data["cek"] = True
    update.callback_query.message.reply_text("Masukkan kode order")