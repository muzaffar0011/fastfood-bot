"""Fast food buyurtma boti.

Ishga tushirish (Command Prompt, shu papka ichida):
  py -m pip install "python-telegram-bot>=21"
  set BOT_TOKEN=yangi_botning_tokeni
  set ADMIN_CHAT_ID=sizning_chat_id
  py bot.py
"""
import os  
import logging
from telegram import (Update, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove,
                      InlineKeyboardButton, InlineKeyboardMarkup)
from telegram.ext import (Application, CommandHandler, MessageHandler, CallbackQueryHandler,
                          ConversationHandler, ContextTypes, filters)

logging.basicConfig(level=logging.INFO)

TOKEN = os.environ["BOT_TOKEN"]
ADMIN_ID = int(os.environ["ADMIN_CHAT_ID"])
# Dastavshiklar guruhi (ixtiyoriy). Guruhga botni qo'shib, /id yozing.
COURIER_ID = int(os.environ["COURIER_CHAT_ID"]) if os.environ.get("COURIER_CHAT_ID") else None
DELIVERY_FEE = 10000  # yetkazib berish narxi (so'm), olib ketishda 0

# Menyuni shu yerda o'zgartiring: bo'lim -> [(taom, narx), ...]
MENU = {
    "Burgerlar": [("Cheeseburger", 28000), ("Double burger", 38000), ("Chicken burger", 26000)],
    "Lavash": [("Mol go'shtli lavash", 32000), ("Tovuqli lavash", 28000), ("Pishloqli lavash", 30000)],
    "Pitsa": [("Margarita", 55000), ("Pepperoni", 68000)],
    "Garnirlar": [("Fri kartoshka", 15000), ("Nuggets (6 ta)", 22000)],
    "Ichimliklar": [("Coca-Cola 0.5", 9000), ("Fanta 0.5", 9000), ("Choy", 6000)],
}
CATS = list(MENU)

BTN_MENU, BTN_CART, BTN_CONTACT = "🍔 Menyu", "🛒 Savat", "☎️ Aloqa"
BTN_DELIVERY, BTN_PICKUP = "🚚 Yetkazib berish", "🏪 Olib ketish"
MAIN_KB = ReplyKeyboardMarkup([[BTN_MENU, BTN_CART], [BTN_CONTACT]], resize_keyboard=True)
CONTACT = "Fast Food\nTelefon: +998 90 123 45 67\nIsh vaqti: har kuni 10:00–23:00"

TYPE, PHONE, ADDR, NOTE = range(4)


def money(n):
    return f"{n:,}".replace(",", " ") + " so'm"


def cart_lines(cart):
    lines, total = [], 0
    for k, q in cart.items():
        i, j = map(int, k.split(":"))
        name, price = MENU[CATS[i]][j]
        lines.append((k, name, price, q))
        total += price * q
    return lines, total


def cats_markup():
    return InlineKeyboardMarkup(
        [[InlineKeyboardButton(c, callback_data=f"cat:{i}")] for i, c in enumerate(CATS)]
        + [[InlineKeyboardButton("🛒 Savat", callback_data="cart")]])


def cart_view(cart):
    if not cart:
        return ("Savat bo'sh. Menyudan taom tanlang.",
                InlineKeyboardMarkup([[InlineKeyboardButton("🍔 Menyu", callback_data="menu")]]))
    lines, total = cart_lines(cart)
    text = ("🛒 Savatingiz:\n\n"
            + "\n".join(f"{n} × {q} = {money(p * q)}" for _, n, p, q in lines)
            + f"\n\nJami: {money(total)}")
    kb = [[InlineKeyboardButton("➖", callback_data=f"q:{k}:-"),
           InlineKeyboardButton(f"{n} × {q}", callback_data="noop"),
           InlineKeyboardButton("➕", callback_data=f"q:{k}:+")] for k, n, p, q in lines]
    kb.append([InlineKeyboardButton("🗑 Tozalash", callback_data="clear"),
               InlineKeyboardButton("✅ Buyurtma berish", callback_data="checkout")])
    kb.append([InlineKeyboardButton("🍔 Menyuga qaytish", callback_data="menu")])
    return text, InlineKeyboardMarkup(kb)


async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Assalomu alaykum! Mazali fast food buyurtma qilish uchun «Menyu» ni bosing.",
        reply_markup=MAIN_KB)


async def show_menu(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Bo'limni tanlang:", reply_markup=cats_markup())


async def show_cart(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    text, kb = cart_view(ctx.user_data.setdefault("cart", {}))
    await update.message.reply_text(text, reply_markup=kb)


async def show_contact(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(CONTACT)


async def on_button(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    d = q.data
    cart = ctx.user_data.setdefault("cart", {})
    if d == "noop":
        await q.answer()
        return
    if d == "menu":
        await q.answer()
        await q.edit_message_text("Bo'limni tanlang:", reply_markup=cats_markup())
        return
    if d.startswith("cat:"):
        i = int(d[4:])
        await q.answer()
        kb = [[InlineKeyboardButton(f"{n} — {money(p)}", callback_data=f"add:{i}:{j}")]
              for j, (n, p) in enumerate(MENU[CATS[i]])]
        kb.append([InlineKeyboardButton("⬅️ Orqaga", callback_data="menu"),
                   InlineKeyboardButton("🛒 Savat", callback_data="cart")])
        await q.edit_message_text(f"{CATS[i]}. Qo'shish uchun bosing:",
                                  reply_markup=InlineKeyboardMarkup(kb))
        return
    if d.startswith("add:"):
        _, i, j = d.split(":")
        k = f"{i}:{j}"
        cart[k] = cart.get(k, 0) + 1
        await q.answer(f"Savatga qo'shildi: {MENU[CATS[int(i)]][int(j)][0]}")
        return
    if d.startswith("q:"):
        p = d.split(":")
        k = f"{p[1]}:{p[2]}"
        if p[3] == "+":
            cart[k] = cart.get(k, 0) + 1
        else:
            cart[k] = cart.get(k, 0) - 1
            if cart[k] <= 0:
                cart.pop(k, None)
    elif d == "clear":
        cart.clear()
    await q.answer()
    text, kb = cart_view(cart)
    await q.edit_message_text(text, reply_markup=kb)


# ---- Buyurtma berish ----
async def checkout(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    if not ctx.user_data.get("cart"):
        await q.message.reply_text("Savat bo'sh.")
        return ConversationHandler.END
    kb = ReplyKeyboardMarkup([[BTN_DELIVERY, BTN_PICKUP]], resize_keyboard=True, one_time_keyboard=True)
    await q.message.reply_text("Buyurtmani qanday olasiz?", reply_markup=kb)
    return TYPE


async def get_type(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    t = update.message.text
    if t not in (BTN_DELIVERY, BTN_PICKUP):
        await update.message.reply_text("Iltimos, tugmalardan birini tanlang.")
        return TYPE
    ctx.user_data["type"] = t
    kb = ReplyKeyboardMarkup([[KeyboardButton("📞 Raqamni yuborish", request_contact=True)]],
                             resize_keyboard=True, one_time_keyboard=True)
    await update.message.reply_text("Telefon raqamingizni yuboring yoki yozing.", reply_markup=kb)
    return PHONE


async def get_phone(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    m = update.message
    ctx.user_data["phone"] = m.contact.phone_number if m.contact else m.text.strip()
    if ctx.user_data["type"] == BTN_DELIVERY:
        kb = ReplyKeyboardMarkup([[KeyboardButton("📍 Joylashuvni yuborish", request_location=True)]],
                                 resize_keyboard=True, one_time_keyboard=True)
        await m.reply_text(
            "📍 Joylashuvingizni yuboring: dastavshik aynan shu nuqtaga keladi.\n"
            "Pastdagi tugmani bosing (kompyuterda: 📎 → Location). Xohlasangiz, manzilni yozib ham yuborishingiz mumkin.",
            reply_markup=kb)
        return ADDR
    ctx.user_data["address"] = "Olib ketadi"
    ctx.user_data["loc"] = None
    return await finish(update, ctx)


async def get_addr(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    m = update.message
    if m.location:
        ctx.user_data["loc"] = (m.location.latitude, m.location.longitude)
        kb = ReplyKeyboardMarkup([["Yo'q"]], resize_keyboard=True, one_time_keyboard=True)
        await m.reply_text("Mo'ljal yoki kvartira/podyezd raqamini yozing (masalan: 3-podyezd, 25-xonadon). "
                           "Kerak bo'lmasa «Yo'q» ni bosing.", reply_markup=kb)
        return NOTE
    ctx.user_data["loc"] = None
    ctx.user_data["address"] = m.text.strip() + " (joylashuv yuborilmadi)"
    return await finish(update, ctx)


async def get_note(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    note = update.message.text.strip()
    addr = "Xaritadagi nuqta"
    if note.lower() not in ("yo'q", "yoq", "yo’q"):
        addr += f", {note}"
    ctx.user_data["address"] = addr
    return await finish(update, ctx)


async def finish(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    u = update.effective_user
    d = ctx.user_data
    lines, total = cart_lines(d["cart"])
    fee = DELIVERY_FEE if d["type"] == BTN_DELIVERY else 0
    n = ctx.bot_data["n"] = ctx.bot_data.get("n", 0) + 1
    items = "\n".join(f"• {nm} × {q} = {money(p * q)}" for _, nm, p, q in lines)
    maplink = ""
    if d.get("loc"):
        maplink = f"\n🗺 https://maps.google.com/?q={d['loc'][0]},{d['loc'][1]}"
    text = (f"🆕 Buyurtma #{n}\n👤 {u.full_name} (@{u.username or '—'})\n📞 {d['phone']}\n"
            f"{d['type']}\n📍 {d['address']}{maplink}\n\n{items}\n\n"
            f"Taomlar: {money(total)}\nYetkazish: {money(fee)}\nJami: {money(total + fee)}")
    kb = InlineKeyboardMarkup([[
        InlineKeyboardButton("✅ Qabul", callback_data=f"st:{n}:acc"),
        InlineKeyboardButton("🍳 Tayyor", callback_data=f"st:{n}:ready")],
        [InlineKeyboardButton("🚚 Yo'lda", callback_data=f"st:{n}:way"),
         InlineKeyboardButton("🎉 Yetkazildi", callback_data=f"st:{n}:done")]])
    await ctx.bot.send_message(ADMIN_ID, text, reply_markup=kb)
    if d.get("loc"):
        await ctx.bot.send_location(ADMIN_ID, latitude=d["loc"][0], longitude=d["loc"][1])
    if COURIER_ID and d["type"] == BTN_DELIVERY:
        ctext = (f"🛵 Yangi buyurtma #{n}\n📍 {d['address']}{maplink}\n📞 {d['phone']}\n\n"
                 f"{items}\n\nJami: {money(total + fee)}")
        ckb = InlineKeyboardMarkup([[InlineKeyboardButton("🚚 Men yetkazaman", callback_data=f"take:{n}")]])
        await ctx.bot.send_message(COURIER_ID, ctext, reply_markup=ckb)
        if d.get("loc"):
            await ctx.bot.send_location(COURIER_ID, latitude=d["loc"][0], longitude=d["loc"][1])
    ctx.bot_data.setdefault("orders", {})[n] = update.effective_chat.id
    d["cart"] = {}
    await update.message.reply_text(
        f"Rahmat! Buyurtma #{n} qabul qilindi.\nJami: {money(total + fee)}. Tez orada bog'lanamiz.",
        reply_markup=MAIN_KB)
    return ConversationHandler.END


async def cancel(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Bekor qilindi.", reply_markup=MAIN_KB)
    return ConversationHandler.END


STATUS = {"acc": "✅ qabul qilindi", "ready": "🍳 tayyor", "way": "🚚 yo'lda", "done": "🎉 yetkazildi. Yoqimli ishtaha!"}


async def on_status(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    if q.from_user.id != ADMIN_ID:
        await q.answer("Ruxsat yo'q", show_alert=True)
        return
    _, n, s = q.data.split(":")
    chat = ctx.bot_data.get("orders", {}).get(int(n))
    if chat:
        await ctx.bot.send_message(chat, f"Buyurtma #{n}: {STATUS[s]}")
        await q.answer("Mijozga xabar yuborildi")
    else:
        await q.answer("Mijoz topilmadi (bot qayta ishga tushgan bo'lishi mumkin)", show_alert=True)


async def on_take(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    n = int(q.data.split(":")[1])
    taken = ctx.bot_data.setdefault("taken", {})
    if n in taken:
        await q.answer(f"Bu buyurtmani {taken[n]} olgan", show_alert=True)
        return
    name = q.from_user.full_name
    taken[n] = name
    await q.answer("Buyurtma sizga biriktirildi")
    await q.edit_message_text(q.message.text + f"\n\n✅ Yetkazadi: {name}")
    chat = ctx.bot_data.get("orders", {}).get(n)
    if chat:
        await ctx.bot.send_message(chat, f"Buyurtma #{n}: dastavshik {name} buyurtmangizni olib ketdi 🛵")
    await ctx.bot.send_message(ADMIN_ID, f"Buyurtma #{n} ni {name} oldi.")


async def chat_id(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(f"Chat ID: {update.effective_chat.id}")


def main():
    b = (Application.builder().token(TOKEN)
         .connect_timeout(30).read_timeout(30).write_timeout(30).pool_timeout(30)
         .get_updates_connect_timeout(30).get_updates_read_timeout(30))
    proxy = os.environ.get("PROXY_URL")  # ixtiyoriy
    if proxy:
        b = b.proxy(proxy).get_updates_proxy(proxy)
    app = b.build()

    text = filters.TEXT & ~filters.COMMAND
    nav = filters.Regex(f"^({BTN_MENU}|{BTN_CART}|{BTN_CONTACT})$")
    conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(checkout, pattern=r"^checkout$")],
        states={
            TYPE: [MessageHandler(text & ~nav, get_type)],
            PHONE: [MessageHandler(filters.CONTACT | (text & ~nav), get_phone)],
            ADDR: [MessageHandler(filters.LOCATION | (text & ~nav), get_addr)],
            NOTE: [MessageHandler(text & ~nav, get_note)],
        },
        fallbacks=[CommandHandler("cancel", cancel), MessageHandler(nav, cancel)],
    )
    app.add_handler(conv)
    app.add_handler(CallbackQueryHandler(on_status, pattern=r"^st:"))
    app.add_handler(CallbackQueryHandler(on_take, pattern=r"^take:"))
    app.add_handler(CommandHandler("id", chat_id))
    app.add_handler(CallbackQueryHandler(on_button, pattern=r"^(menu|cat:|add:|q:|clear|cart|noop)"))
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.Regex(f"^{BTN_MENU}$"), show_menu))
    app.add_handler(MessageHandler(filters.Regex(f"^{BTN_CART}$"), show_cart))
    app.add_handler(MessageHandler(filters.Regex(f"^{BTN_CONTACT}$"), show_contact))
    app.run_polling(bootstrap_retries=-1)


if __name__ == "__main__":
    main()
