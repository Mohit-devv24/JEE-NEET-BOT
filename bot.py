import os
import sys
import socket

# Force IPv4 on macOS to eliminate 15-30s IPv6 DNS timeouts
_orig_getaddrinfo = socket.getaddrinfo
def _ipv4_getaddrinfo(*args, **kwargs):
    responses = _orig_getaddrinfo(*args, **kwargs)
    ipv4_res = [r for r in responses if r[0] == socket.AF_INET]
    return ipv4_res if ipv4_res else responses
socket.getaddrinfo = _ipv4_getaddrinfo

import json
import re
import math
import time
import datetime
import telebot
from telebot import types, apihelper

apihelper.READ_TIMEOUT = 300
apihelper.CONNECT_TIMEOUT = 30
apihelper.CUSTOM_REQUEST_TIMEOUT = (30, 300)

TOKEN = os.environ.get("BOT_TOKEN", "8996284156:AAEl6oYSxqszHXUP-yS7FKBTYq5g3tKLLIo")
CHANNEL_STORAGE_ID = -1004467297667
bot = telebot.TeleBot(TOKEN, parse_mode="HTML")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MANIFEST_PATH = os.path.join(BASE_DIR, "files_manifest.json")
DOWNLOADS_DIR = os.path.join(BASE_DIR, "downloaded_files")
USERS_DB_PATH = os.path.join(BASE_DIR, "users_db.json")
WELCOME_BANNER_PATH = os.path.join(BASE_DIR, "welcome_banner_640x360.jpg")
if not os.path.exists(WELCOME_BANNER_PATH):
    WELCOME_BANNER_PATH = os.path.join(BASE_DIR, "welcome_banner.jpg")

BOT_USERNAME = "materialwallahbot"
FREE_DOWNLOADS_LIMIT = 4
REQUIRED_REFERRALS = 3
ADMIN_IDS = [8371163996, 5893196884]  # Owner & Admin IDs

# Required Channels for Force Subscription
REQUIRED_CHANNELS = [
    {
        "id": "-1004417334756",
        "name": "IIT JEE NEET MATERIAL",
        "link": "https://t.me/+iJmYmHYEqgk0ODAx"
    },
    {
        "id": "@jee_neet_discussion_student",
        "name": "JEE NEET Discussion",
        "link": "https://t.me/jee_neet_discussion_student"
    }
]

# States
broadcast_states = {}   # admin_chat_id -> True
request_states = {}     # user_id -> True
payment_states = {}     # user_id -> True
reply_states = {}       # admin_chat_id -> target_user_id

# ================= USER DATABASE ================= #

TG_CACHE_PATH = os.path.join(BASE_DIR, "telegram_file_cache.json")
tg_cache = {}
if os.path.exists(TG_CACHE_PATH):
    try:
        with open(TG_CACHE_PATH, "r", encoding="utf-8") as f:
            tg_cache = json.load(f)
    except Exception:
        tg_cache = {}

def save_tg_cache():
    try:
        with open(TG_CACHE_PATH, "w", encoding="utf-8") as f:
            json.dump(tg_cache, f, indent=2)
    except Exception as e:
        print("Error saving telegram cache:", e)

users_data = {}
if os.path.exists(USERS_DB_PATH):
    try:
        with open(USERS_DB_PATH, "r", encoding="utf-8") as f:
            users_data = json.load(f)
    except Exception:
        users_data = {}

last_db_backup_time = 0
last_pinned_backup_id = None
backup_lock = threading.Lock()

def load_cloud_db():
    """Load persistent users database from Telegram Cloud Storage Channel."""
    global users_data, last_pinned_backup_id
    try:
        chat = bot.get_chat(CHANNEL_STORAGE_ID)
        pinned = chat.pinned_message
        if pinned and pinned.document and pinned.caption and '#DB_PERSISTENCE_MASTER' in pinned.caption:
            last_pinned_backup_id = pinned.message_id
            file_info = bot.get_file(pinned.document.file_id)
            content = bot.download_file(file_info.file_path)
            cloud_users = json.loads(content.decode('utf-8'))
            if isinstance(cloud_users, dict):
                # Merge cloud data with any local data
                for uid, udata in cloud_users.items():
                    if uid not in users_data or udata.get("downloads_count", 0) > users_data[uid].get("downloads_count", 0):
                        users_data[uid] = udata
                print(f"✅ Loaded {len(users_data)} users from Telegram Cloud Master DB!", flush=True)
                with open(USERS_DB_PATH, "w", encoding="utf-8") as f:
                    json.dump(users_data, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print("Cloud DB load error (falling back to local):", e, flush=True)

def backup_db_to_cloud():
    """Backup users database to Telegram Cloud and pin it as master persistence."""
    global last_db_backup_time, last_pinned_backup_id
    with backup_lock:
        now = time.time()
        # Debounce: avoid uploading more than once every 15 seconds
        if now - last_db_backup_time < 15:
            return
        last_db_backup_time = now

        try:
            temp_db_path = f"/tmp/users_db_cloud_{int(now)}.json"
            with open(temp_db_path, "w", encoding="utf-8") as f:
                json.dump(users_data, f, indent=2, ensure_ascii=False)

            with open(temp_db_path, "rb") as f:
                doc_msg = bot.send_document(
                    CHANNEL_STORAGE_ID,
                    f,
                    caption=f"#DB_PERSISTENCE_MASTER | Users: {len(users_data)} | {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                )

            if doc_msg and doc_msg.message_id:
                old_id = last_pinned_backup_id
                bot.pin_chat_message(CHANNEL_STORAGE_ID, doc_msg.message_id)
                last_pinned_backup_id = doc_msg.message_id
                if old_id and old_id != doc_msg.message_id:
                    try:
                        bot.delete_message(CHANNEL_STORAGE_ID, old_id)
                    except Exception:
                        pass

            if os.path.exists(temp_db_path):
                os.remove(temp_db_path)
        except Exception as e:
            print("Failed to backup DB to Telegram Cloud:", e, flush=True)

# Initial load from cloud DB
load_cloud_db()

def save_users():
    try:
        with open(USERS_DB_PATH, "w", encoding="utf-8") as f:
            json.dump(users_data, f, indent=2, ensure_ascii=False)
        threading.Thread(target=backup_db_to_cloud, daemon=True).start()
    except Exception as e:
        print("Error saving users db:", e)

def notify_admins(text, markup=None):
    for admin_id in ADMIN_IDS:
        try:
            bot.send_message(admin_id, text, reply_markup=markup, parse_mode="HTML")
        except Exception as e:
            print(f"Failed to alert admin {admin_id}:", e)

@bot.chat_join_request_handler()
def handle_chat_join_request(req):
    """Record that user sent join request for bot access, without auto-approving in the channel!"""
    try:
        uid_str = str(req.from_user.id)
        if uid_str not in users_data:
            users_data[uid_str] = {
                "first_name": req.from_user.first_name or "Student",
                "username": req.from_user.username or "",
                "downloads_count": 0,
                "referrals": [],
                "referral_count": 0,
                "referred_by": None,
                "is_unlimited": False,
                "joined_at": int(time.time()),
            }
        users_data[uid_str]["req_sent"] = True
        users_data[uid_str]["is_verified"] = True
        save_users()
    except Exception as e:
        print("Join request recording error:", e)

def is_user_subscribed(user_id):
    if int(user_id) in ADMIN_IDS:
        return True
    
    uid_str = str(user_id)
    u_info = users_data.get(uid_str, {})
    
    # If already verified in bot, permanently grant access without touching channel!
    if u_info.get("is_verified", False) or u_info.get("req_sent", False) or u_info.get("is_unlimited", False):
        return True
    
    # Check Discussion Group membership
    try:
        m = bot.get_chat_member('@jee_neet_discussion_student', user_id)
        if m.status in ['left', 'kicked']:
            return False
    except Exception:
        pass

    return False

def show_force_sub_screen(chat_id, user_id, message_id=None):
    text = (
        "⚠️ <b>MEMBERSHIP REQUIRED TO ACCESS MATERIALS!</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "To use <b>JEE NEET Books</b> and access 1,376+ free books, notes & test series, "
        "complete these 2 simple steps:\n\n"
        "1️⃣ <b>Send Join Request to Official Channel:</b>\n"
        "   👉 Tap '1. Request to Join Channel' below and press <i>'Request to Join'</i>\n\n"
        "2️⃣ <b>Join Discussion Group:</b>\n"
        "   👉 Tap '2. Join Discussion Group' below & join the group\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "👇 <i>After sending the request and joining, tap 'Verify My Access'!</i>"
    )

    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(
        types.InlineKeyboardButton("📢 1. Request to Join Channel", url="https://t.me/+iJmYmHYEqgk0ODAx"),
        types.InlineKeyboardButton("💬 2. Join Discussion Group", url="https://t.me/jee_neet_discussion_student"),
        types.InlineKeyboardButton("🔄 Verify My Access", callback_data="verify_subscription")
    )

    if message_id:
        try:
            bot.edit_message_text(text, chat_id, message_id, reply_markup=markup)
            return
        except Exception:
            pass
    bot.send_message(chat_id, text, reply_markup=markup)

def get_or_create_user(user_id, first_name="", username="", referrer_id=None):
    uid_str = str(user_id)
    is_new = uid_str not in users_data

    if is_new:
        users_data[uid_str] = {
            "first_name": first_name or "Student",
            "username": username or "",
            "downloads_count": 0,
            "referrals": [],
            "referral_count": 0,
            "referred_by": None,
            "is_unlimited": int(user_id) in ADMIN_IDS,
            "joined_at": int(time.time())
        }

        referrer_name = "Direct / Organic"
        if referrer_id and str(referrer_id) != uid_str and str(referrer_id) in users_data:
            ref_str = str(referrer_id)
            referrer = users_data[ref_str]
            users_data[uid_str]["referred_by"] = ref_str
            referrer_name = f"Referred by {referrer.get('first_name', 'User')} (ID: {ref_str})"

            if uid_str not in referrer.get("referrals", []):
                referrer["referrals"].append(uid_str)
                referrer["referral_count"] = len(referrer["referrals"])

                if referrer["referral_count"] >= REQUIRED_REFERRALS:
                    referrer["is_unlimited"] = True
                    try:
                        bot.send_message(
                            int(ref_str),
                            "🎉 <b>CONGRATULATIONS! UNLIMITED ACCESS UNLOCKED!</b> 🔓\n\n"
                            f"Your 3rd friend just joined using your invite link!\n\n"
                            "🌟 <b>All download limits have been removed forever.</b>\n"
                            "You now have <b>Lifetime Unlimited Access</b> to all 1,376+ books, notes, and modules!\n\n"
                            "Happy Studying & Best of Luck! 🚀"
                        )
                    except Exception as e:
                        print("Failed to notify referrer:", e)
                else:
                    needed = REQUIRED_REFERRALS - referrer["referral_count"]
                    try:
                        bot.send_message(
                            int(ref_str),
                            "🎉 <b>Great News! A friend just joined!</b>\n\n"
                            f"👤 <b>{first_name}</b> started StudyMate using your invite link.\n\n"
                            f"📊 <b>Your Progress:</b> [ {referrer['referral_count']} / {REQUIRED_REFERRALS} Friends ]\n"
                            f"⚡ Invite <b>{needed} more friend(s)</b> to unlock <b>Lifetime Unlimited Downloads!</b>"
                        )
                    except Exception as e:
                        print("Failed to notify referrer:", e)

        save_users()

        # Real-time Admin Alert
        now_str = datetime.datetime.now().strftime("%d %b %Y, %I:%M %p")
        user_handle = f"@{username}" if username else "No username"
        admin_alert = (
            "🔔 <b>NEW USER JOINED!</b>\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"👤 <b>Name:</b> {first_name}\n"
            f"🏷️ <b>Username:</b> {user_handle}\n"
            f"🆔 <b>User ID:</b> <code>{user_id}</code>\n"
            f"🔗 <b>Source:</b> {referrer_name}\n"
            f"👥 <b>Total Bot Users:</b> <code>{len(users_data)}</code>\n"
            f"⏰ <b>Joined:</b> {now_str}\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━"
        )
        notify_admins(admin_alert)

    else:
        if first_name:
            users_data[uid_str]["first_name"] = first_name
        if username:
            users_data[uid_str]["username"] = username
        if int(user_id) in ADMIN_IDS:
            users_data[uid_str]["is_unlimited"] = True

    return users_data[uid_str], is_new

admin_student_mode = {}  # admin_id -> True/False

def can_user_download(user_id):
    uid_str = str(user_id)
    if int(user_id) in ADMIN_IDS and not admin_student_mode.get(int(user_id), False):
        return True, users_data.get(uid_str, {})
    
    user = users_data.get(uid_str)
    if not user:
        user, _ = get_or_create_user(user_id)

    if user.get("is_unlimited", False) and not admin_student_mode.get(int(user_id), False):
        return True, user
    
    downloads = user.get("downloads_count", 0)
    if downloads < FREE_DOWNLOADS_LIMIT:
        return True, user
    
    return False, user

# ================= CATALOG DATA ================= #

files_db = []
if os.path.exists(MANIFEST_PATH):
    with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
        files_db = json.load(f)
print(f"Loaded {len(files_db)} files from manifest.")

def clean_name(s):
    if not s:
        return ""
    s = s.replace("ðŸ“š", "📚").replace("âžª", "➔").replace("Ar!hant", "Arihant")
    s = s.replace("ð", "").replace("â", "").replace("Â", "").replace("ï", "").strip()
    return re.sub(r'\s+', ' ', s)

categories = {}
for f in files_db:
    path_parts = [p.strip() for p in clean_name(f["path"]).split("/") if p.strip()]
    if not path_parts:
        continue
    root = path_parts[0]
    sub = path_parts[1] if len(path_parts) > 2 else "General"
    
    if root not in categories:
        categories[root] = {}
    if sub not in categories[root]:
        categories[root][sub] = []
    
    f["clean_name"] = clean_name(f["name"])
    f["clean_path"] = clean_name(f["path"])
    categories[root][sub].append(f)

def find_local_file(file_info):
    name = file_info["name"]
    clean_p = clean_name(file_info["path"])
    p1 = os.path.join(DOWNLOADS_DIR, clean_p)
    if os.path.exists(p1) and os.path.getsize(p1) > 1000:
        return p1
    p2 = os.path.join(DOWNLOADS_DIR, file_info["path"])
    if os.path.exists(p2) and os.path.getsize(p2) > 1000:
        return p2
    for root, _, files in os.walk(DOWNLOADS_DIR):
        for fl in files:
            if fl == name or clean_name(fl) == clean_name(name):
                fp = os.path.join(root, fl)
                if os.path.getsize(fp) > 1000:
                    return fp
    return None

def get_invite_link(user_id):
    return f"https://t.me/{BOT_USERNAME}?start=ref_{user_id}"

def get_share_url(user_id):
    link = get_invite_link(user_id)
    text = (
        "🔥 Hey! Download original IIT-JEE & NEET-UG Textbooks, Coaching Modules & PYQs "
        "directly on Telegram for FREE! Get 4 Free Books instantly here 👇\n"
    )
    import urllib.parse
    return f"https://t.me/share/url?url={urllib.parse.quote(link)}&text={urllib.parse.quote(text)}"

# ================= ADMIN PANEL HANDLERS ================= #

@bot.message_handler(commands=['admin'])
def handle_admin_panel(message):
    if message.from_user.id not in ADMIN_IDS:
        bot.send_message(message.chat.id, "⛔ Access denied. You are not authorized as an Admin.")
        return
    show_admin_dashboard(message.chat.id)

def show_admin_dashboard(chat_id, message_id=None):
    total_users = len(users_data)
    total_downloads = sum(u.get("downloads_count", 0) for u in users_data.values())
    unlimited_users = sum(1 for u in users_data.values() if u.get("is_unlimited"))
    
    local_count = 0
    if os.path.exists(DOWNLOADS_DIR):
        for _, _, files in os.walk(DOWNLOADS_DIR):
            local_count += len([f for f in files if f.endswith(".pdf")])

    text = (
        "🛠️ <b>ADMIN CONTROL DASHBOARD</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"👥 <b>Total Registered Users:</b> <code>{total_users}</code>\n"
        f"📥 <b>Total Books Downloaded:</b> <code>{total_downloads}</code>\n"
        f"🔓 <b>VIP Unlimited Members:</b> <code>{unlimited_users}</code>\n"
        f"⚡ <b>Local Downloaded Books:</b> <code>{local_count}</code> / {len(files_db)}\n"
        f"🚀 <b>Bot Polling Status:</b> <code>Online & Active</code>\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "Select an administrative action below:"
    )

    markup = types.InlineKeyboardMarkup(row_width=2)
    btn_broadcast = types.InlineKeyboardButton("📢 Broadcast Message", callback_data="admin:broadcast_prompt")
    btn_users = types.InlineKeyboardButton("👥 View Recent Users", callback_data="admin:recent_users")
    btn_stats = types.InlineKeyboardButton("📊 Detailed Stats", callback_data="admin:detailed_stats")
    btn_refresh = types.InlineKeyboardButton("🔄 Refresh Dashboard", callback_data="admin:refresh")

    markup.add(btn_broadcast)
    markup.add(btn_users, btn_stats)
    markup.add(btn_refresh)

    if message_id:
        try:
            bot.edit_message_text(text, chat_id, message_id, reply_markup=markup)
            return
        except Exception:
            pass
    bot.send_message(chat_id, text, reply_markup=markup)

@bot.message_handler(commands=['broadcast'])
def handle_broadcast_cmd(message):
    if message.from_user.id not in ADMIN_IDS:
        return
    prompt_broadcast(message.chat.id)

def prompt_broadcast(chat_id):
    broadcast_states[chat_id] = True
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("❌ Cancel Broadcast", callback_data="admin:cancel_broadcast"))
    bot.send_message(
        chat_id,
        "📢 <b>BROADCAST TO ALL USERS</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"Send the message, photo, document, or forward any message that you want to broadcast to <b>ALL {len(users_data)} registered students</b>.\n\n"
        "<i>(Type /cancel or click Cancel below to abort)</i>",
        reply_markup=markup
    )

@bot.message_handler(commands=['studentmode'])
def handle_student_mode(message):
    if message.from_user.id not in ADMIN_IDS:
        return
    admin_id = message.from_user.id
    current = admin_student_mode.get(admin_id, False)
    admin_student_mode[admin_id] = not current
    mode_str = "ON 👨‍🎓 (Student Limit 4 books active)" if admin_student_mode[admin_id] else "OFF 🛡️ (Admin Unlimited Active)"
    bot.send_message(message.chat.id, f"🛠️ <b>Student Test Mode:</b> {mode_str}\n\nType /start to see student main menu, or /resetlimit to reset your quota to 0/4.")

@bot.message_handler(commands=['resetlimit'])
def handle_reset_limit(message):
    if message.from_user.id not in ADMIN_IDS:
        return
    uid_str = str(message.from_user.id)
    if uid_str in users_data:
        users_data[uid_str]["downloads_count"] = 0
        save_users()
    bot.send_message(message.chat.id, "🔄 <b>Your download limit has been reset to 0/4!</b>")

@bot.message_handler(commands=['cancel'])
def handle_cancel(message):
    chat_id = message.chat.id
    cancelled = False
    if chat_id in broadcast_states:
        del broadcast_states[chat_id]
        cancelled = True
    if chat_id in request_states:
        del request_states[chat_id]
        cancelled = True
    if chat_id in payment_states:
        del payment_states[chat_id]
        cancelled = True
    if chat_id in reply_states:
        del reply_states[chat_id]
        cancelled = True
    if cancelled:
        bot.send_message(chat_id, "❌ Action cancelled.")
    else:
        bot.send_message(chat_id, "ℹ️ No active action to cancel.")

def execute_broadcast(admin_chat_id, message):
    if admin_chat_id in broadcast_states:
        del broadcast_states[admin_chat_id]

    status_msg = bot.send_message(admin_chat_id, f"🚀 <b>Broadcasting to {len(users_data)} users...</b>\nPlease wait.")
    sent = 0
    failed = 0

    for uid in list(users_data.keys()):
        try:
            target_id = int(uid)
            bot.copy_message(target_id, message.chat.id, message.message_id)
            sent += 1
            time.sleep(0.04)
        except Exception:
            failed += 1

    summary = (
        "✅ <b>BROADCAST COMPLETED!</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"📤 <b>Successfully Delivered:</b> <code>{sent}</code>\n"
        f"❌ <b>Blocked / Failed:</b> <code>{failed}</code>\n"
        f"👥 <b>Total Audience:</b> <code>{len(users_data)}</code>\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━"
    )
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("🛠️ Return to Admin Dashboard", callback_data="admin:refresh"))
    bot.edit_message_text(summary, admin_chat_id, status_msg.message_id, reply_markup=markup)

# ================= USER COMMAND HANDLERS ================= #

@bot.message_handler(commands=['start'])
def handle_start(message):
    user_id = message.from_user.id
    first_name = message.from_user.first_name or "Aspirant"
    username = message.from_user.username or ""

    # Parse referral or direct file parameter
    referrer_id = None
    direct_file_id = None
    args = message.text.split()
    if len(args) > 1:
        param = args[1]
        if param.startswith("ref_"):
            try:
                referrer_id = int(param.replace("ref_", ""))
            except ValueError:
                referrer_id = None
        elif param.startswith("file_"):
            direct_file_id = param.replace("file_", "")

    user, is_new = get_or_create_user(user_id, first_name, username, referrer_id)

    # If direct file requested via inline search
    if direct_file_id:
        if not is_user_subscribed(user_id):
            show_force_sub_screen(message.chat.id, user_id)
            return
        send_file_to_user(message.chat.id, user_id, direct_file_id)
        return

    # Check force channel subscription
    if not is_user_subscribed(user_id):
        show_force_sub_screen(message.chat.id, user_id)
        return

    show_main_menu(message.chat.id, user_id, first_name)

def get_main_reply_keyboard(user_id=None):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    b1 = types.KeyboardButton("🎯 IIT-JEE")
    b2 = types.KeyboardButton("🩺 NEET-UG")
    b3 = types.KeyboardButton("🌟 Mix Crunch")
    b4 = types.KeyboardButton("🔍 Search Materials")
    b5 = types.KeyboardButton("🎁 Free Quota & Invite")
    b6 = types.KeyboardButton("💳 Buy VIP (₹49)")
    b7 = types.KeyboardButton("📝 Request Material")
    b8 = types.KeyboardButton("👨‍💻 Student Support")
    b9 = types.KeyboardButton("📊 Bot Stats")
    b10 = types.KeyboardButton("ℹ️ Help & FAQ")

    markup.add(b1, b2)
    markup.add(b3, b4)
    markup.add(b5, b6)
    markup.add(b7, b8)
    if user_id and int(user_id) in ADMIN_IDS:
        b_admin = types.KeyboardButton("🛠️ Admin Panel")
        markup.add(b9, b10)
        markup.add(b_admin)
    else:
        markup.add(b9, b10)
    return markup

def show_category_menu(chat_id, cat_name):
    subcats = categories.get(cat_name, {})
    markup = types.InlineKeyboardMarkup(row_width=1)
    for sub_name, flist in sorted(subcats.items()):
        label = f"📁 {sub_name} ({len(flist)})"
        markup.add(types.InlineKeyboardButton(label, callback_data=f"subcat:{cat_name}:{sub_name[:20]}"))
    markup.add(types.InlineKeyboardButton("⬅️ Back to Main Menu", callback_data="main_menu"))
    bot.send_message(chat_id, f"📂 <b>{cat_name} Sections:</b>\nChoose a topic below to view available materials:", reply_markup=markup, parse_mode="HTML")

def show_main_menu(chat_id, user_id, first_name="Aspirant", message_id=None):
    user, _ = get_or_create_user(user_id)
    downloads_used = user.get("downloads_count", 0)
    free_left = max(0, FREE_DOWNLOADS_LIMIT - downloads_used)
    is_unlimited_active = user.get("is_unlimited") and not admin_student_mode.get(int(user_id), False)
    if is_unlimited_active:
        status_str = "🌟 <b>VIP Unlimited</b>"
    elif free_left == 0:
        status_str = "🔒 <b>0/4 Free Quota (Locked - Refer 3 Friends or VIP)</b>"
    else:
        status_str = f"🎁 <b>{free_left}/{FREE_DOWNLOADS_LIMIT} Free Downloads Left</b>"

    welcome_text = (
        f"👋 <b>Welcome {first_name} to JEE NEET Books! 📚</b>\n\n"
        f"Your ultimate preparation library for <b>IIT-JEE & NEET-UG</b> examinations.\n\n"
        f"⚡ <b>Available Library:</b> <code>{len(files_db)}</code> Premium Books & Modules\n"
        f"📊 <b>Your Account Status:</b> {status_str}\n\n"
        f"📂 <b>Key Materials Available:</b>\n"
        f" • 🎯 <b>IIT-JEE:</b> Coaching Modules, Cengage, Physics Galaxy, Kota Notes\n"
        f" • 🩺 <b>NEET-UG:</b> PW Modules, 34-39 Yrs PYQs, NCERT Simplifiers\n"
        f" • 🌟 <b>Mix Crunch:</b> Handbooks & CBSE Champions\n\n"
        f"👇 <i>Select any option from the bottom menu to get started!</i>"
    )

    reply_kb = get_main_reply_keyboard(user_id)

    if message_id:
        try:
            bot.delete_message(chat_id, message_id)
        except Exception:
            pass

    if os.path.exists(WELCOME_BANNER_PATH):
        try:
            with open(WELCOME_BANNER_PATH, "rb") as banner:
                bot.send_photo(chat_id, banner, caption=welcome_text, reply_markup=reply_kb, parse_mode="HTML")
            return
        except Exception as e:
            print("Failed to send welcome banner photo:", e)

    bot.send_message(chat_id, welcome_text, reply_markup=reply_kb, parse_mode="HTML")

@bot.message_handler(commands=['invite', 'quota', 'profile'])
def handle_invite(message):
    show_quota_screen(message.chat.id, message.from_user.id)

def show_quota_screen(chat_id, user_id, message_id=None):
    user, _ = get_or_create_user(user_id)
    downloads_used = user.get("downloads_count", 0)
    referrals = user.get("referral_count", 0)
    is_unlimited = user.get("is_unlimited", False)
    invite_link = get_invite_link(user_id)
    share_url = get_share_url(user_id)

    if is_unlimited:
        text = (
            "🌟 <b>VIP UNLIMITED MEMBERSHIP ACTIVE!</b> 🔓\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "✅ <b>Status:</b> Lifetime Unlimited Access\n"
            f"📥 <b>Books Downloaded:</b> {downloads_used}\n"
            f"👥 <b>Friends Invited:</b> {referrals}\n\n"
            "You have complete access to all 1,376+ books, notes, and coaching modules with zero limits!\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"🔗 <b>Your Invite Link:</b>\n<code>{invite_link}</code>"
        )
        markup = types.InlineKeyboardMarkup(row_width=1)
        markup.add(types.InlineKeyboardButton("📲 Share with Friends on Telegram", url=share_url))
        markup.add(types.InlineKeyboardButton("🏠 Back to Main Menu", callback_data="main_menu"))
    else:
        free_left = max(0, FREE_DOWNLOADS_LIMIT - downloads_used)
        needed = max(0, REQUIRED_REFERRALS - referrals)
        progress_bar = "█" * referrals + "░" * needed

        text = (
            "🎁 <b>YOUR ACCOUNT & DOWNLOAD QUOTA</b>\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"📥 <b>Free Downloads Left:</b> <b>{free_left} / {FREE_DOWNLOADS_LIMIT}</b>\n"
            f"👥 <b>Friends Invited:</b> <b>{referrals} / {REQUIRED_REFERRALS}</b>\n"
            f"📊 <b>Unlock Progress:</b> [ {progress_bar} ]\n\n"
            f"⚡ <b>Want Lifetime Unlimited Access?</b>\n"
            f"Option 1: Invite <b>{needed} more friend(s)</b> (100% FREE)\n"
            f"Option 2: Get Instant VIP Pass for only <b>₹49</b>!\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"🔗 <b>Your Personal Invite Link:</b>\n"
            f"<code>{invite_link}</code>"
        )
        markup = types.InlineKeyboardMarkup(row_width=1)
        markup.add(types.InlineKeyboardButton("📲 Share with Friends on Telegram", url=share_url))
        markup.add(types.InlineKeyboardButton("💳 Buy Instant VIP Pass (₹49)", callback_data="action:buy_vip"))
        markup.add(types.InlineKeyboardButton("🔄 Refresh Status", callback_data="action:quota"))
        markup.add(types.InlineKeyboardButton("🏠 Back to Main Menu", callback_data="main_menu"))

    if message_id:
        try:
            bot.edit_message_text(text, chat_id, message_id, reply_markup=markup)
            return
        except Exception:
            pass
    bot.send_message(chat_id, text, reply_markup=markup)

@bot.message_handler(commands=['request'])
def handle_request_cmd(message):
    start_material_request(message.chat.id)

def start_material_request(chat_id):
    request_states[chat_id] = True
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("❌ Cancel", callback_data="action:cancel_request"))
    bot.send_message(
        chat_id,
        "📝 <b>REQUEST STUDY MATERIAL / BOOKS</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "Can't find a specific book, coaching module, or formula sheet?\n\n"
        "Send the <b>Book Title, Author, or Coaching Name</b> below.\n"
        "Our team will search, index, and upload it to the bot for you!\n\n"
        "<i>(Type /cancel to abort)</i>",
        reply_markup=markup
    )

def show_vip_purchase_screen(chat_id, user_id, message_id=None):
    text = (
        "💳 <b>INSTANT VIP LIFETIME UNLIMITED PASS</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "Unlock <b>LIFETIME UNLIMITED ACCESS</b> to all 1,376+ Books, Notes, Coaching Modules & PYQs with zero referrals!\n\n"
        "⚡ <b>One-Time Fee:</b> <b>₹49 Only</b> (Valid Forever)\n\n"
        "📲 <b>How to Pay:</b>\n"
        "1️⃣ Pay <b>₹49</b> via any UPI App (GPay / PhonePe / Paytm / BHIM) to:\n"
        "   👉 <code>goyal.com@fam</code> <i>(Tap to copy)</i>\n\n"
        "2️⃣ Take a screenshot of the successful payment.\n"
        "3️⃣ Tap <b>'Upload Payment Screenshot'</b> below and send your screenshot here!\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "<i>Our admin will verify and activate your VIP access in minutes!</i>\n"
        "Need help? Contact support: @athther"
    )

    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(types.InlineKeyboardButton("📤 Upload Payment Screenshot", callback_data="action:upload_screenshot"))
    markup.add(types.InlineKeyboardButton("💬 Contact Support (@athther)", url="https://t.me/athther"))
    markup.add(types.InlineKeyboardButton("🔙 Back to Main Menu", callback_data="main_menu"))

    if message_id:
        try:
            bot.edit_message_text(text, chat_id, message_id, reply_markup=markup)
            return
        except Exception:
            pass
    bot.send_message(chat_id, text, reply_markup=markup)

@bot.message_handler(commands=['help'])
def handle_help(message):
    text = (
        "📖 <b>JEE NEET Books Quick Guide & Commands:</b>\n\n"
        "1️⃣ <b>Browse Materials:</b> Click /start to explore IIT-JEE, NEET-UG, and Mix Crunch categories.\n\n"
        "2️⃣ <b>Direct Search:</b> Simply send any book title or topic in this chat. For example:\n"
        "   • <code>Physics Galaxy</code>\n"
        "   • <code>Arihant Mathematics</code>\n"
        "   • <code>Allen Modules</code>\n"
        "   • <code>Biology NCERT</code>\n"
        "   • <code>PYQ 2024</code>\n\n"
        "3️⃣ <b>Inline Search:</b> Type <code>@materialwallahbot physics</code> in ANY chat or group to share books instantly!\n\n"
        "4️⃣ <b>Request Material:</b> Use /request to ask for any study material not yet in our library.\n\n"
        "5️⃣ <b>Download Policy:</b>\n"
        "   • Every student gets <b>4 FREE demo downloads</b>.\n"
        "   • Invite <b>3 friends</b> OR buy the <b>₹49 VIP Pass</b> for Lifetime Unlimited Access!"
    )
    bot.send_message(message.chat.id, text)

@bot.message_handler(commands=['stats'])
def handle_stats(message):
    jee_count = sum(len(sub) for sub in categories.get("IIT-JEE", {}).values())
    neet_count = sum(len(sub) for sub in categories.get("NEET-UG", {}).values())
    mix_count = sum(len(sub) for sub in categories.get("Mix Crunch", {}).values())
    
    local_count = 0
    if os.path.exists(DOWNLOADS_DIR):
        for _, _, files in os.walk(DOWNLOADS_DIR):
            local_count += len([f for f in files if f.endswith(".pdf")])

    total_users = len(users_data)
    unlimited_users = sum(1 for u in users_data.values() if u.get("is_unlimited"))

    text = (
        "📊 <b>JEE NEET Books Statistics</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"📚 <b>Total Materials Indexed:</b> <code>{len(files_db)}</code>\n"
        f"🎯 <b>IIT-JEE Materials:</b> <code>{jee_count}</code>\n"
        f"🩺 <b>NEET-UG Materials:</b> <code>{neet_count}</code>\n"
        f"🌟 <b>Mix Crunch Materials:</b> <code>{mix_count}</code>\n"
        f"⚡ <b>Ready Instant Downloads:</b> <code>{local_count}</code> Books\n"
        f"👥 <b>Total Active Students:</b> <code>{total_users}</code>\n"
        f"🔓 <b>VIP Unlimited Members:</b> <code>{unlimited_users}</code>\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "🚀 <i>Status: High-Speed Official Servers Connected</i>"
    )
    bot.send_message(message.chat.id, text)

# ================= CALLBACK QUERY HANDLER ================= #

@bot.callback_query_handler(func=lambda call: True)
def handle_callbacks(call):
    data = call.data
    user_id = call.from_user.id
    chat_id = call.message.chat.id

    # Force Subscription Verification
    if data == "verify_subscription":
        # Check if member in discussion group
        is_in_group = False
        try:
            m = bot.get_chat_member('@jee_neet_discussion_student', user_id)
            if m.status in ['creator', 'administrator', 'member', 'restricted']:
                is_in_group = True
        except Exception as e:
            print("Error checking group member:", e)

        if not is_in_group:
            bot.answer_callback_query(
                call.id,
                "❌ Please join the Discussion Group (@jee_neet_discussion_student) first!",
                show_alert=True
            )
            return

        # Mark Channel Join Request and permanent verification in bot (channel request remains pending)
        uid_str = str(user_id)
        if uid_str in users_data:
            users_data[uid_str]["req_sent"] = True
            users_data[uid_str]["is_verified"] = True
            save_users()

        bot.answer_callback_query(call.id, "🎉 Verified! Access Granted!", show_alert=False)
        show_main_menu(chat_id, user_id, call.from_user.first_name, message_id=call.message.message_id)
        return

    # Check subscription for all other actions
    if not is_user_subscribed(user_id):
        bot.answer_callback_query(call.id, "Please join required channels first.")
        show_force_sub_screen(chat_id, user_id, message_id=call.message.message_id)
        return

    # Admin actions
    if data.startswith("admin:"):
        if user_id not in ADMIN_IDS:
            bot.answer_callback_query(call.id, "Unauthorized.")
            return

        action = data.split(":", 1)[1]
        if action == "refresh":
            show_admin_dashboard(chat_id, call.message.message_id)
            bot.answer_callback_query(call.id, "Refreshed!")
        elif action == "broadcast_prompt":
            prompt_broadcast(chat_id)
            bot.answer_callback_query(call.id)
        elif action == "cancel_broadcast":
            if chat_id in broadcast_states:
                del broadcast_states[chat_id]
            bot.answer_callback_query(call.id, "Broadcast cancelled.")
            show_admin_dashboard(chat_id, call.message.message_id)
        elif action == "recent_users":
            bot.answer_callback_query(call.id)
            u_list = list(users_data.items())[-10:]
            msg_lines = ["👥 <b>RECENT USERS (Last 10):</b>\n"]
            for uid, info in reversed(u_list):
                u_h = f"@{info.get('username')}" if info.get('username') else "No username"
                unl = "🔓 VIP" if info.get('is_unlimited') else f"🎁 {info.get('downloads_count',0)}/4 dl"
                msg_lines.append(f"• <b>{info.get('first_name', 'User')}</b> ({u_h}) | <code>{uid}</code>\n  {unl} | Ref: {info.get('referral_count', 0)}")
            
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton("🔙 Back to Dashboard", callback_data="admin:refresh"))
            bot.edit_message_text("\n".join(msg_lines), chat_id, call.message.message_id, reply_markup=markup)
        elif action == "detailed_stats":
            handle_stats(call.message)
            bot.answer_callback_query(call.id)
        elif action.startswith("approve_vip_"):
            target_uid = action.replace("approve_vip_", "")
            if target_uid in users_data:
                users_data[target_uid]["is_unlimited"] = True
                save_users()
                bot.answer_callback_query(call.id, f"VIP Approved for {target_uid}!")
                bot.edit_message_caption(
                    f"✅ <b>VIP APPROVED for User ID:</b> <code>{target_uid}</code>\nAccess has been activated!",
                    chat_id,
                    call.message.message_id
                )
                try:
                    bot.send_message(
                        int(target_uid),
                        "🎉 <b>CONGRATULATIONS! YOUR ₹49 VIP PASS IS ACTIVATED!</b> 🔓\n\n"
                        "Your payment has been successfully verified by Admin!\n"
                        "🌟 You now have <b>Lifetime Unlimited Access</b> to all 1,376+ Books & Modules!\n\n"
                        "Happy Studying & Best of Luck for IIT-JEE / NEET! 🚀"
                    )
                except Exception as e:
                    print("Failed to notify VIP user:", e)
        elif action.startswith("decline_vip_"):
            target_uid = action.replace("decline_vip_", "")
            bot.answer_callback_query(call.id, f"Payment declined for {target_uid}")
            bot.edit_message_caption(
                f"❌ <b>VIP Payment Declined for User ID:</b> <code>{target_uid}</code>",
                chat_id,
                call.message.message_id
            )
            try:
                bot.send_message(
                    int(target_uid),
                    "⚠️ <b>VIP Verification Failed:</b> Your payment screenshot could not be verified. "
                    "If you believe this is an error, please contact admin or try again."
                )
            except Exception:
                pass
        return

    # User Actions
    if data == "main_menu":
        show_main_menu(chat_id, user_id, call.from_user.first_name, message_id=call.message.message_id)

    elif data == "action:quota":
        show_quota_screen(chat_id, user_id, call.message.message_id)
        bot.answer_callback_query(call.id)

    elif data == "action:buy_vip":
        show_vip_purchase_screen(chat_id, user_id, call.message.message_id)
        bot.answer_callback_query(call.id)

    elif data == "action:upload_screenshot":
        payment_states[chat_id] = True
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("❌ Cancel", callback_data="action:cancel_payment"))
        bot.send_message(
            chat_id,
            "📸 <b>Send Payment Screenshot:</b>\n\nPlease upload the screenshot of your ₹49 UPI payment now.\n\n<i>(Type /cancel to abort)</i>",
            reply_markup=markup
        )
        bot.answer_callback_query(call.id)

    elif data == "action:cancel_payment":
        if chat_id in payment_states:
            del payment_states[chat_id]
        bot.answer_callback_query(call.id, "Cancelled.")
        show_main_menu(chat_id, user_id, call.from_user.first_name)

    elif data == "action:request_material":
        start_material_request(chat_id)
        bot.answer_callback_query(call.id)

    elif data == "action:cancel_request":
        if chat_id in request_states:
            del request_states[chat_id]
        bot.answer_callback_query(call.id, "Request cancelled.")
        show_main_menu(chat_id, user_id, call.from_user.first_name)

    elif data == "action:search_hint":
        bot.answer_callback_query(call.id)
        bot.send_message(
            chat_id,
            "🔍 <b>Direct Book Search:</b>\n\nSimply send any title, author, or publisher name in this chat.\n\nExamples:\n• <code>Physics Galaxy</code>\n• <code>Arihant Chemistry</code>\n• <code>Allen Test Series</code>\n• <code>NEET PYQ 2024</code>"
        )

    elif data == "action:stats":
        handle_stats(call.message)
        bot.answer_callback_query(call.id)

    elif data == "action:help":
        handle_help(call.message)
        bot.answer_callback_query(call.id)

    elif data.startswith("cat:"):
        cat_name = data.split(":", 1)[1]
        subcats = categories.get(cat_name, {})

        markup = types.InlineKeyboardMarkup(row_width=1)
        for sub_name, flist in sorted(subcats.items()):
            label = f"📁 {sub_name} ({len(flist)})"
            markup.add(types.InlineKeyboardButton(label, callback_data=f"subcat:{cat_name}:{sub_name[:20]}"))

        markup.add(types.InlineKeyboardButton("⬅️ Back to Main Menu", callback_data="main_menu"))

        bot.edit_message_text(
            f"📂 <b>{cat_name} Sections:</b>\nChoose a topic below to view available materials:",
            chat_id,
            call.message.message_id,
            reply_markup=markup
        )

    elif data.startswith("subcat:"):
        parts = data.split(":")
        cat_name = parts[1]
        sub_prefix = parts[2]
        
        subcats = categories.get(cat_name, {})
        full_sub = None
        for k in subcats.keys():
            if k.startswith(sub_prefix):
                full_sub = k
                break

        if not full_sub:
            bot.answer_callback_query(call.id, "Section not found.")
            return

        file_list = subcats[full_sub]
        page = int(parts[3]) if len(parts) > 3 else 0
        show_file_list_page(call.message, file_list, title=f"{cat_name} > {full_sub}", page=page, callback_prefix=f"subcat:{cat_name}:{sub_prefix}")

    elif data.startswith("page:"):
        parts = data.split(":")
        q = parts[1]
        page = int(parts[2])
        results = search_files(q)
        show_file_list_page(call.message, results, title=f"Results for '{q}'", page=page, callback_prefix=f"page:{q}")

    elif data.startswith("file:"):
        file_id = data.split(":", 1)[1]
        send_file_to_user(chat_id, user_id, file_id)
        bot.answer_callback_query(call.id)

def show_file_list_page(message, file_list, title, page=0, callback_prefix=""):
    PER_PAGE = 8
    total_pages = math.ceil(len(file_list) / PER_PAGE)
    start = page * PER_PAGE
    end = min(start + PER_PAGE, len(file_list))

    curr_files = file_list[start:end]

    markup = types.InlineKeyboardMarkup(row_width=1)
    for f in curr_files:
        name = clean_name(f["name"])
        if len(name) > 38:
            name = name[:35] + "..."
        local = find_local_file(f)
        icon = "⚡" if (f["id"] in tg_cache or local) else "📄"
        markup.add(types.InlineKeyboardButton(f"{icon} {name}", callback_data=f"file:{f['id']}"))

    nav_buttons = []
    if page > 0:
        nav_buttons.append(types.InlineKeyboardButton("⬅️ Prev", callback_data=f"{callback_prefix}:{page-1}"))
    nav_buttons.append(types.InlineKeyboardButton(f"📄 {page+1}/{total_pages}", callback_data="noop"))
    if page < total_pages - 1:
        nav_buttons.append(types.InlineKeyboardButton("Next ➡️", callback_data=f"{callback_prefix}:{page+1}"))

    if nav_buttons:
        markup.row(*nav_buttons)

    markup.add(types.InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu"))

    bot.edit_message_text(
        f"📚 <b>{title}</b>\n(Showing {start+1}-{end} of {len(file_list)} items)\n\n<i>⚡ = Ready PDF Download | 📄 = Cloud Access</i>",
        message.chat.id,
        message.message_id,
        reply_markup=markup
    )

def send_file_to_user(chat_id, user_id, file_id):
    allowed, user = can_user_download(user_id)
    if not allowed:
        referrals = user.get("referral_count", 0)
        needed = max(0, REQUIRED_REFERRALS - referrals)
        progress_bar = "█" * referrals + "░" * needed
        invite_link = get_invite_link(user_id)
        share_url = get_share_url(user_id)

        lock_text = (
            "🔒 <b>FREE TRIAL LIMIT REACHED (4/4 Books Used)</b>\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "You have enjoyed your <b>4 Free Demo Downloads</b>! 📚\n\n"
            "To unlock <b>LIFETIME UNLIMITED ACCESS</b> to all 1,376+ Books, Notes, Coaching Modules & PYQs:\n\n"
            f"👉 <b>Option 1:</b> Invite {REQUIRED_REFERRALS} friends (FREE)\n"
            f"   Progress: [ {progress_bar} ] ({referrals}/{REQUIRED_REFERRALS} Friends)\n\n"
            f"👉 <b>Option 2:</b> Get Instant VIP Pass for only <b>₹49</b>!\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"🔗 <b>Your Personal Invite Link:</b>\n"
            f"<code>{invite_link}</code>"
        )

        markup = types.InlineKeyboardMarkup(row_width=1)
        markup.add(types.InlineKeyboardButton("📲 Share with Friends on Telegram", url=share_url))
        markup.add(types.InlineKeyboardButton("💳 Buy Instant VIP Pass (₹49)", callback_data="action:buy_vip"))
        markup.add(types.InlineKeyboardButton("🔄 Refresh / Check Status", callback_data="action:quota"))
        markup.add(types.InlineKeyboardButton("🏠 Back to Main Menu", callback_data="main_menu"))

        bot.send_message(chat_id, lock_text, reply_markup=markup)
        return

    target = None
    for f in files_db:
        if f["id"] == file_id:
            target = f
            break
    if not target:
        bot.send_message(chat_id, "❌ File details not found.")
        return

    name = clean_name(target["name"])
    local_path = find_local_file(target)

    is_unlimited_active = user.get("is_unlimited", False) and not admin_student_mode.get(int(user_id), False)
    if not is_unlimited_active:
        user["downloads_count"] = user.get("downloads_count", 0) + 1
        save_users()
        remaining = max(0, FREE_DOWNLOADS_LIMIT - user["downloads_count"])
        quota_caption = f"🎁 <i>Free Quota: {remaining} free download(s) remaining.</i>"
    else:
        quota_caption = "🌟 <i>VIP Unlimited Member</i>"

    # 1. Instant delivery via Telegram Cloud Cache
    if file_id in tg_cache:
        val = tg_cache[file_id]
        if isinstance(val, int) or (isinstance(val, dict) and "msg_id" in val):
            m_id = val["msg_id"] if isinstance(val, dict) else val
            try:
                bot.copy_message(chat_id, CHANNEL_STORAGE_ID, m_id)
                return
            except Exception as e:
                print(f"Failed to copy message {m_id} for {name}: {e}")
        elif isinstance(val, str):
            try:
                bot.send_document(
                    chat_id,
                    val,
                    caption=f"📘 <b>{name}</b>",
                    parse_mode="HTML"
                )
                return
            except Exception as e:
                print(f"Cached file_id invalid for {name}: {e}")
                tg_cache.pop(file_id, None)
                save_tg_cache()

    # 2. Local File Upload
    if local_path:
        file_size_mb = os.path.getsize(local_path) / (1024 * 1024)
        if file_size_mb <= 49.5:
            bot.send_chat_action(chat_id, "upload_document")
            msg = bot.send_message(chat_id, f"⚡ <b>Sending {name}...</b>")
            try:
                with open(local_path, "rb") as doc:
                    sent_msg = bot.send_document(
                        chat_id,
                        doc,
                        caption=f"📘 <b>{name}</b>",
                        parse_mode="HTML",
                        timeout=300
                    )
                if sent_msg and sent_msg.document:
                    tg_cache[file_id] = sent_msg.document.file_id
                    save_tg_cache()
                try:
                    bot.delete_message(chat_id, msg.message_id)
                except Exception:
                    pass
                return
            except Exception as e:
                print("Upload error:", e)
                try:
                    bot.delete_message(chat_id, msg.message_id)
                except Exception:
                    pass

    drive_link = f"https://drive.google.com/file/d/{file_id}/view?usp=sharing"
    direct_link = f"https://drive.google.com/uc?id={file_id}&export=download"

    size_str = ""
    if local_path and os.path.exists(local_path):
        size_mb = os.path.getsize(local_path) / (1024 * 1024)
        size_str = f" ({size_mb:.1f} MB)"
    elif target.get("size"):
        size_mb = target["size"] / (1024 * 1024)
        size_str = f" ({size_mb:.1f} MB)"

    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(
        types.InlineKeyboardButton("⬇️ Direct Download PDF", url=direct_link),
        types.InlineKeyboardButton("🌐 Open in Google Drive", url=drive_link)
    )

    bot.send_message(
        chat_id,
        f"📘 <b>{name}</b>{size_str}",
        reply_markup=markup
    )

# ================= INLINE MODE HANDLER ================= #

@bot.inline_handler(lambda query: True)
def handle_inline_search(inline_query):
    q = inline_query.query.strip()
    results = []

    matches = search_files(q) if q else files_db[:20]

    for idx, f in enumerate(matches[:25]):
        name = clean_name(f["name"])
        path = clean_name(f["path"])
        fid = f["id"]

        caption = (
            f"📘 <b>{name}</b>\n\n"
            f"📁 <b>Category:</b> <code>{path}</code>\n\n"
            f"⚡ <i>Available for direct download on @{BOT_USERNAME}</i>"
        )

        markup = types.InlineKeyboardMarkup()
        markup.add(
            types.InlineKeyboardButton("📥 Download PDF via Bot", url=f"https://t.me/{BOT_USERNAME}?start=file_{fid}")
        )

        r = types.InlineQueryResultArticle(
            id=str(idx),
            title=name,
            description=path,
            input_message_content=types.InputTextMessageContent(caption, parse_mode="HTML"),
            reply_markup=markup
        )
        results.append(r)

    bot.answer_inline_query(inline_query.id, results, cache_time=10)

# ================= SEARCH & ALL-PURPOSE MESSAGE HANDLER ================= #

def search_files(query):
    q_tokens = [t.lower() for t in query.split() if t.strip()]
    matches = []
    for f in files_db:
        name_lower = clean_name(f["name"]).lower()
        path_lower = clean_name(f["path"]).lower()
        if all(token in name_lower or token in path_lower for token in q_tokens):
            matches.append(f)
    return matches

@bot.channel_post_handler(func=lambda message: True)
def handle_channel_post(message):
    print(f"🔥 CHANNEL POST DETECTED! Chat ID: {message.chat.id}, Title: {getattr(message.chat, 'title', 'Channel')}")
    try:
        bot.send_message(message.chat.id, f"✅ Storage Dump Connected! Channel ID: <code>{message.chat.id}</code>")
    except Exception as e:
        print("Failed to reply in channel:", e)

@bot.message_handler(func=lambda message: getattr(message, 'forward_from_chat', None) is not None)
def handle_forwarded_post(message):
    chat = message.forward_from_chat
    bot.reply_to(message, f"📌 <b>Detected Channel:</b> {chat.title}\n🆔 <b>Channel ID:</b> <code>{chat.id}</code>\n\n✅ Dump storage ID saved!")

@bot.message_handler(func=lambda message: True, content_types=['text', 'photo', 'document', 'video', 'audio', 'voice', 'forward'])
def handle_incoming_messages(message):
    user_id = message.from_user.id
    chat_id = message.chat.id
    first_name = message.from_user.first_name or "Student"
    username = message.from_user.username or ""

    # Check broadcast mode
    if user_id in ADMIN_IDS and chat_id in broadcast_states:
        execute_broadcast(chat_id, message)
        return

    # Check payment screenshot upload mode
    if chat_id in payment_states:
        del payment_states[chat_id]
        bot.send_message(
            chat_id,
            "✅ <b>Payment screenshot received!</b>\n\n"
            "Our admin team is verifying your payment. Your <b>Lifetime VIP Unlimited Access</b> "
            "will be activated shortly! Thank you! 🌟"
        )
        now_str = datetime.datetime.now().strftime("%d %b %Y, %I:%M %p")
        u_h = f"@{username}" if username else "No username"
        caption = (
            "💰 <b>NEW VIP PAYMENT SUBMITTED (₹49)!</b>\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"👤 <b>Student:</b> {first_name} ({u_h})\n"
            f"🆔 <b>User ID:</b> <code>{user_id}</code>\n"
            f"⏰ <b>Time:</b> {now_str}\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "Review screenshot and choose an action:"
        )
        markup = types.InlineKeyboardMarkup(row_width=2)
        markup.add(
            types.InlineKeyboardButton("✅ Approve VIP", callback_data=f"admin:approve_vip_{user_id}"),
            types.InlineKeyboardButton("❌ Decline", callback_data=f"admin:decline_vip_{user_id}")
        )
        for aid in ADMIN_IDS:
            try:
                if message.photo:
                    bot.send_photo(aid, message.photo[-1].file_id, caption=caption, reply_markup=markup, parse_mode="HTML")
                else:
                    bot.send_message(aid, caption, reply_markup=markup, parse_mode="HTML")
            except Exception as e:
                print("Failed to send payment to admin:", e)
        return

    # Check study material request mode
    if chat_id in request_states:
        del request_states[chat_id]
        req_text = message.text or "[Non-text attachment]"
        bot.send_message(
            chat_id,
            f"✅ <b>Request Received!</b>\n\n"
            f"We have noted your request for:\n<i>\"{req_text}\"</i>\n\n"
            f"Our team will search and upload it to the library soon! 📚"
        )
        now_str = datetime.datetime.now().strftime("%d %b %Y, %I:%M %p")
        u_h = f"@{username}" if username else "No username"
        alert_text = (
            "📩 <b>NEW STUDY MATERIAL REQUEST!</b>\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"👤 <b>Student:</b> {first_name} ({u_h})\n"
            f"🆔 <b>User ID:</b> <code>{user_id}</code>\n"
            f"📖 <b>Requested:</b>\n<i>\"{req_text}\"</i>\n"
            f"⏰ <b>Time:</b> {now_str}\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━"
        )
        notify_admins(alert_text)
        return

    # Check force channel subscription for regular text messages
    if not is_user_subscribed(user_id):
        show_force_sub_screen(chat_id, user_id)
        return

    # Normal user text search and Reply Keyboard actions
    if message.content_type == 'text':
        txt = message.text.strip()
        if txt == "🎯 IIT-JEE":
            show_category_menu(chat_id, "IIT-JEE")
            return
        elif txt == "🩺 NEET-UG":
            show_category_menu(chat_id, "NEET-UG")
            return
        elif txt == "🌟 Mix Crunch":
            show_category_menu(chat_id, "Mix Crunch")
            return
        elif txt == "🔍 Search Materials":
            bot.send_message(chat_id, "🔍 <b>Direct Book Search:</b>\nSimply send any book title, author, or topic here (e.g. <code>Physics Galaxy</code>, <code>Cengage</code>, <code>Allen</code>):", parse_mode="HTML")
            return
        elif txt == "🎁 Free Quota & Invite":
            show_quota_screen(chat_id, user_id)
            return
        elif txt == "💳 Buy VIP (₹49)":
            show_vip_purchase_screen(chat_id, user_id)
            return
        elif txt == "📝 Request Material":
            start_material_request(chat_id)
            return
        elif txt == "👨‍💻 Student Support":
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton("💬 Open Chat with @athther", url="https://t.me/athther"))
            bot.send_message(
                chat_id,
                "👨‍💻 <b>STUDENT HELPDESK & SUPPORT</b>\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                "Have any questions, issues with downloads, or need help with VIP activation?\n\n"
                "You can directly chat with our founder & administrator:\n"
                "👉 <b>Telegram:</b> @athther\n\n"
                "<i>Click below to open direct chat!</i>",
                reply_markup=markup,
                parse_mode="HTML"
            )
            return
        elif txt == "📊 Bot Stats":
            handle_stats(message)
            return
        elif txt == "ℹ️ Help & FAQ":
            handle_help(message)
            return
        elif txt == "🛠️ Admin Panel" and user_id in ADMIN_IDS:
            show_admin_dashboard(chat_id)
            return

        query = txt
        if len(query) < 2:
            bot.send_message(chat_id, "⚠️ Please enter at least 2 characters to search.")
            return

        results = search_files(query)
        if not results:
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton("📝 Request This Material", callback_data="action:request_material"))
            markup.add(types.InlineKeyboardButton("🏠 Back to Main Menu", callback_data="main_menu"))
            bot.send_message(
                chat_id,
                f"❌ <b>No materials found matching '{query}'.</b>\n\n"
                f"Would you like to request our team to upload this book for you?",
                reply_markup=markup
            )
            return

        msg = bot.send_message(chat_id, f"🔍 Searching library for <b>{query}</b>...")
        show_file_list_page(msg, results, title=f"Search Results for '{query}'", page=0, callback_prefix=f"page:{query}")

@bot.chat_join_request_handler(func=lambda req: True)
def handle_chat_join_request(req):
    uid_str = str(req.from_user.id)
    if uid_str in users_data:
        users_data[uid_str]["req_sent"] = True
        save_users()

import threading
from http.server import HTTPServer, BaseHTTPRequestHandler

class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/plain')
        self.end_headers()
        self.wfile.write(b"JEE NEET Books Bot is Running Healthy!")
    def log_message(self, format, *args):
        pass

def start_health_server():
    port = int(os.environ.get("PORT", 8080))
    try:
        server = HTTPServer(("0.0.0.0", port), HealthHandler)
        server.serve_forever()
    except Exception as e:
        print("Health server error:", e)

threading.Thread(target=start_health_server, daemon=True).start()

if __name__ == "__main__":
    print("🤖 JEE NEET Books Bot is running with Force Join, Inline Mode, Requests & VIP System...")
    while True:
        try:
            bot.infinity_polling(timeout=20, long_polling_timeout=15, allowed_updates=['message', 'callback_query', 'inline_query', 'chat_join_request'])
        except Exception as e:
            print("Polling reconnecting after error:", e)
            time.sleep(3)
