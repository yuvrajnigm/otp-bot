import os, json
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
from core.panel_manager import create_panel, remove_panel, load_panels

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID"))

user_states = {}

def is_admin(uid): 
    return uid == ADMIN_ID

async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🤖 OTP Panel Bot Active")

# ---------- ADD PANEL (MODERN FLOW) ----------
async def addpanel(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id): return
    user_states[update.effective_user.id] = {"step": "mode"}
    await update.message.reply_text(
        "🧩 New Panel Setup\n\n"
        "Select OTP Mode:\n"
        "1️⃣ SMS Only\n"
        "2️⃣ Call Only\n"
        "3️⃣ SMS + Call"
    )

async def panel_flow(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if uid not in user_states: return

    state = user_states[uid]
    txt = update.message.text.strip()

    if state["step"] == "mode":
        state["mode"] = {"1":"sms","2":"call","3":"sms_call"}.get(txt)
        state["step"] = "login"
        await update.message.reply_text(
            "🔐 Login Type:\n1️⃣ Username + Password\n2️⃣ Email + Password"
        )

    elif state["step"] == "login":
        state["login"] = "userpass" if txt=="1" else "emailpass"
        state["step"] = "name"
        await update.message.reply_text("📛 Enter Panel Name:")

    elif state["step"] == "name":
        state["name"] = txt
        state["step"] = "base"
        await update.message.reply_text("🌐 Enter Base URL:")

    elif state["step"] == "base":
        state["base"] = txt
        state["step"] = "sms_api" if state["mode"]!="call" else "call_api"
        await update.message.reply_text(
            "📩 Enter SMS API:" if state["mode"]!="call" else "📞 Enter Call API:"
        )

    elif state["step"] == "sms_api":
        state["sms_api"] = txt
        if state["mode"]=="sms_call":
            state["step"] = "call_api"
            await update.message.reply_text("📞 Enter Call API:")
        else:
            pid = create_panel(state)
            del user_states[uid]
            await update.message.reply_text(f"✅ Panel Added\nID: {pid}")

    elif state["step"] == "call_api":
        state["call_api"] = txt
        pid = create_panel(state)
        del user_states[uid]
        await update.message.reply_text(f"✅ Panel Added\nID: {pid}")

# ---------- REMOVE PANEL ----------
async def removepanel(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id): return
    if not ctx.args:
        await update.message.reply_text("Usage: /removepanel PANEL_ID")
        return
    ok = remove_panel(ctx.args[0])
    await update.message.reply_text("✅ Removed" if ok else "❌ Not Found")

# ---------- LIST PANELS ----------
async def panels(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    p = load_panels()
    if not p:
        await update.message.reply_text("No panels")
        return
    msg = "🧩 Panels:\n\n"
    for k,v in p.items():
        msg += f"{k} | {v['name']} | {v['mode']}\n"
    await update.message.reply_text(msg)

# ---------- RUN ----------
app = ApplicationBuilder().token(BOT_TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("addpanel", addpanel))
app.add_handler(CommandHandler("removepanel", removepanel))
app.add_handler(CommandHandler("panels", panels))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, panel_flow))

app.run_polling()
