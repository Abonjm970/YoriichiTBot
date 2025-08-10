import nest_asyncio
import logging
import json
import os
import random
import asyncio
import sys
import traceback

from telegram import Update, ChatPermissions, BotCommand
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
    ConversationHandler,
)

# تهيئة تسجيل المعلومات
logging.basicConfig(level=logging.INFO)

# ملفات البيانات
REPLIES_FILE = "replies.json"
WARNINGS_FILE = "warnings.json"
CHAT_IDS_FILE = "chat_ids.json"
BANNED_USERS_FILE = "banned_users.json"
PUBLIC_REPLIES_FILE = "replies.json"

DEVELOPER_ID = #عنوان ID الخاص بالمطور

#سينشئ البوت ملفات لحفظ معلومات كل مجموعة على حدة
print("🚀 البوت بدأ التشغيل...")

# التقاط أي استثناء غير متوقع
def handle_exception(exc_type, exc_value, exc_traceback):
    print("❌ حصل خطأ غير متوقع:")
    traceback.print_exception(exc_type, exc_value, exc_traceback)

sys.excepthook = handle_exception

# --- وظائف التحميل والحفظ لكل مجموعة ---
def get_replies_file(chat_id):
    return f"replies_{chat_id}.json"

def get_warnings_file(chat_id):
    return f"warnings_{chat_id}.json"

def get_banned_users_file(chat_id):
    return f"banned_users_{chat_id}.json"

def load_replies(chat_id):
    file = get_replies_file(chat_id)
    if os.path.exists(file):
        with open(file, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_replies(chat_id, data):
    with open(get_replies_file(chat_id), "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def load_warnings(chat_id):
    file = get_warnings_file(chat_id)
    if os.path.exists(file):
        with open(file, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_warnings(chat_id, data):
    with open(get_warnings_file(chat_id), "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def load_chat_ids():
    if os.path.exists(CHAT_IDS_FILE):
        with open(CHAT_IDS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

def save_chat_ids(data):
    with open(CHAT_IDS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f)

def load_banned_users(chat_id):
    file = get_banned_users_file(chat_id)
    if os.path.exists(file):
        with open(file, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_banned_users(chat_id, data):
    with open(get_banned_users_file(chat_id), "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

chat_ids = load_chat_ids()

# --- دوال مساعدة ---
async def is_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type == "private":
        return False
    member = await context.bot.get_chat_member(update.effective_chat.id, update.effective_user.id)
    return member.status in ["administrator", "creator"]

async def get_target_user_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # إذا كانت الرسالة رد
    if update.message.reply_to_message:
        return update.message.reply_to_message.from_user.id
    # إذا جت معرّف كوسيط
    if context.args and context.args[0].isdigit():
        return int(context.args[0])
    # أو في النص نفسه
    if update.message.text:
        parts = update.message.text.split()
        if len(parts) > 1 and parts[1].isdigit():
            return int(parts[1])
    return None

# --- جميع دوال الأوامر ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    cid = update.effective_chat.id
    if cid not in chat_ids:
        chat_ids.append(cid)
        save_chat_ids(chat_ids)
    await update.message.reply_text(
        "يا مرحبا.. بوت يوريتشي لإدارة المجموعات. ارسل /help لاستعراض جميع الاوامر"
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = (
        "/start - بدء البوت\n"
        "/help - عرض هذه القائمة (أو اكتب \"الاوامر\")\n"
        "/mute - كتم المستخدم (بالرد أو بالمعرّف) (أو اكتب \"كتم\")\n"
        "/unmute - فك الكتم (بالرد أو بالمعرّف) (أو اكتب \"فك كتم\")\n"
        "/mutes - عرض قائمة المكتومين (أو اكتب \"المكتومين\")\n"
        "/ban - حظر المستخدم (بالرد أو بالمعرّف) (أو اكتب \"حظر\")\n"
        "/unban - رفع الحظر (بالرد أو بالمعرّف) (أو اكتب \"فك حظر\")\n"
        "/bans - عرض قائمة المحظورين (أو اكتب \"المحظورين\")\n"
        "/warn - تحذير المستخدم (بالرد) (أو اكتب \"تحذير\")\n"
        "/unwarn - إزالة جميع التحذيرات عن المستخدم (بالرد أو بالمعرّف) (أو اكتب \"إزالة تحذير\")\n"
        "/warns - عرض قائمة المنبهين (أو اكتب \"المنبهين\")\n"
        "/del - حذف رسالة (بالرد) (أو اكتب \"حذف\")\n"
        "/pin - تثبيت رسالة (بالرد) (أو اكتب \"تثبيت\")\n"
        "/unpin - إلغاء تثبيت جميع الرسائل (أو اكتب \"إلغاء تثبيت\")\n"
        "/info - عرض معلومات المستخدم (أو اكتب \"معلومات\")\n"
        "/addreply - إضافة رد تلقائي مخصص (أو اكتب \"إضافة رد\")\n"
        "/delreply - حذف رد تلقائي مخصص (أو اكتب \"حذف رد\")\n"
        "/cancel - إلغاء العملية الجارية (أو اكتب \"إلغاء\")"
    )
    if update.effective_user.id == DEVELOPER_ID:
        help_text += "\n\n🔐 أوامر المطور:\n/broadcast - إذاعة وتثبيت رسالة لجميع الدردشات"
    await update.message.reply_text(help_text)

async def mute(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type == "private":
        return await update.message.reply_text("❗️هذا الأمر يعمل فقط داخل المجموعات.")
    if not await is_admin(update, context):
        return await update.message.reply_text("🚫 هذا الأمر للمشرفين فقط.")
    user_id = await get_target_user_id(update, context)
    if not user_id:
        return await update.message.reply_text("❗️ يرجى الرد على رسالة أو تزويدي بالمعرّف الرقمي للمستخدم.")
    if user_id == DEVELOPER_ID:
        return await update.message.reply_text("🚫 لا يمكن تنفيذ هذا الأمر على المطور.")
    try:
        await context.bot.restrict_chat_member(
            update.effective_chat.id,
            user_id,
            permissions=ChatPermissions(can_send_messages=False),
        )
        await update.message.reply_text("✅ تم كتم المستخدم.")
    except Exception as e:
        await update.message.reply_text(f"❌ لم أتمكن من كتم المستخدم. الخطأ: {e}")

async def unmute(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type == "private":
        return await update.message.reply_text("❗️هذا الأمر يعمل فقط داخل المجموعات.")
    if not await is_admin(update, context):
        return await update.message.reply_text("🚫 هذا الأمر للمشرفين فقط.")
    user_id = await get_target_user_id(update, context)
    if not user_id:
        return await update.message.reply_text("❗️ يرجى الرد على رسالة أو تزويدي بالمعرّف الرقمي للمستخدم.")
    try:
        await context.bot.restrict_chat_member(
            update.effective_chat.id,
            user_id,
            permissions=ChatPermissions(can_send_messages=True),
        )
        await update.message.reply_text("✅ تم فك الكتم.")
    except Exception as e:
        await update.message.reply_text(f"❌ لم أتمكن من فك الكتم. الخطأ: {e}")

async def mutes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type == "private":
        return await update.message.reply_text("❗️هذا الأمر يعمل فقط داخل المجموعات.")
    if not await is_admin(update, context):
        return await update.message.reply_text("🚫 هذا الأمر للمشرفين فقط.")
    await update.message.reply_text("📛 لا يمكن جلب قائمة المكتومين تلقائيًا من تيليجرام عبر البوت المجاني.")

async def ban(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type == "private":
        return await update.message.reply_text("❗️هذا الأمر يعمل فقط داخل المجموعات.")
    if not await is_admin(update, context):
        return await update.message.reply_text("🚫 هذا الأمر للمشرفين فقط.")
    user_id = await get_target_user_id(update, context)
    if not user_id:
        return await update.message.reply_text("❗️ يرجى الرد على رسالة أو تزويدي بالمعرّف الرقمي للمستخدم.")
    if user_id == DEVELOPER_ID:
        return await update.message.reply_text("🚫 لا يمكن تنفيذ هذا الأمر على المطور.")
    chat_id = str(update.effective_chat.id)
    banned_users_data = load_banned_users(chat_id)
    user_name = f"Unknown User ({user_id})"
    try:
        member = await context.bot.get_chat_member(update.effective_chat.id, user_id)
        user_name = member.user.full_name
    except:
        pass
    try:
        await context.bot.ban_chat_member(update.effective_chat.id, user_id)
        banned_users_data[str(user_id)] = user_name
        save_banned_users(chat_id, banned_users_data)
        await update.message.reply_text("🚫 تم حظر المستخدم.")
    except Exception as e:
        await update.message.reply_text(f"❌ لم أتمكن من حظر المستخدم. الخطأ: {e}")

async def unban(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type == "private":
        return await update.message.reply_text("❗️هذا الأمر يعمل فقط داخل المجموعات.")
    if not await is_admin(update, context):
        return await update.message.reply_text("🚫 هذا الأمر للمشرفين فقط.")
    user_id = await get_target_user_id(update, context)
    if not user_id:
        return await update.message.reply_text("❗️ يرجى الرد على رسالة أو تزويدي بالمعرّف الرقمي للمستخدم.")
    chat_id = str(update.effective_chat.id)
    banned_users_data = load_banned_users(chat_id)
    try:
        await context.bot.unban_chat_member(update.effective_chat.id, user_id)
        if str(user_id) in banned_users_data:
            del banned_users_data[str(user_id)]
            save_banned_users(chat_id, banned_users_data)
        await update.message.reply_text("✅ تم رفع الحظر.")
    except Exception as e:
        await update.message.reply_text(f"❌ لم أتمكن من رفع الحظر عن المستخدم. الخطأ: {e}")

async def bans(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type == "private":
        return await update.message.reply_text("❗️هذا الأمر يعمل فقط داخل المجموعات.")
    if not await is_admin(update, context):
        return await update.message.reply_text("🚫 هذا الأمر للمشرفين فقط.")
    chat_id = str(update.effective_chat.id)
    banned_users_data = load_banned_users(chat_id)
    if banned_users_data:
        banned_list = "\n".join([f"- {name} (ID: {uid})" for uid, name in banned_users_data.items()])
        await update.message.reply_text(f"🚫 قائمة المحظورين:\n{banned_list}")
    else:
        await update.message.reply_text("✅ لا يوجد محظورون في هذه المجموعة حاليًا.")

async def warn(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type == "private":
        return await update.message.reply_text("❗️هذا الأمر يعمل فقط داخل المجموعات.")
    if not await is_admin(update, context):
        return await update.message.reply_text("🚫 هذا الأمر للمشرفين فقط.")
    target_user_id = None
    target_user_name = None
    if update.message.reply_to_message:
        target_user_id = str(update.message.reply_to_message.from_user.id)
        target_user_name = update.message.reply_to_message.from_user.full_name
    elif context.args and context.args[0].isdigit():
        target_user_id = context.args[0]
        try:
            member = await context.bot.get_chat_member(update.effective_chat.id, int(target_user_id))
            target_user_name = member.user.full_name
        except:
            target_user_name = f"Unknown User ({target_user_id})"
    else:
        return await update.message.reply_text("❗️ يجب الرد على رسالة المستخدم أو تزويدي بمعرفه الرقمي.")
    if int(target_user_id) == DEVELOPER_ID:
        return await update.message.reply_text("🚫 لا يمكن تنفيذ هذا الأمر على المطور.")
    chat_id = str(update.effective_chat.id)
    warnings_data = load_warnings(chat_id)
    warnings_data.setdefault(target_user_id, {"count": 0, "name": target_user_name})
    warnings_data[target_user_id]["count"] += 1
    warnings_data[target_user_id]["name"] = target_user_name
    save_warnings(chat_id, warnings_data)
    if warnings_data[target_user_id]["count"] >= 3:
        try:
            await context.bot.ban_chat_member(update.effective_chat.id, int(target_user_id))
            banned_users_data = load_banned_users(chat_id)
            banned_users_data[target_user_id] = target_user_name
            save_banned_users(chat_id, banned_users_data)
            del warnings_data[target_user_id]
            save_warnings(chat_id, warnings_data)
            await update.message.reply_text(f"🚫 {target_user_name} تم حظره بعد 3 تحذيرات.")
        except Exception as e:
            await update.message.reply_text(f"❌ حدث خطأ أثناء محاولة حظر {target_user_name}: {e}")
    else:
        await update.message.reply_text(f"⚠️ تم تحذير {target_user_name} ({warnings_data[target_user_id]['count']}/3)")

async def unwarn(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type == "private":
        return await update.message.reply_text("❗️هذا الأمر يعمل فقط داخل المجموعات.")
    if not await is_admin(update, context):
        return await update.message.reply_text("🚫 هذا الأمر للمشرفين فقط.")
    target_user_id = None
    target_user_name = None
    if update.message.reply_to_message:
        target_user_id = str(update.message.reply_to_message.from_user.id)
        target_user_name = update.message.reply_to_message.from_user.full_name
    elif context.args and context.args[0].isdigit():
        target_user_id = context.args[0]
        try:
            member = await context.bot.get_chat_member(update.effective_chat.id, int(target_user_id))
            target_user_name = member.user.full_name
        except:
            target_user_name = f"Unknown User ({target_user_id})"
    else:
        return await update.message.reply_text("❗️ يجب الرد على رسالة المستخدم أو تزويدي بمعرفه الرقمي.")
    chat_id = str(update.effective_chat.id)
    warnings_data = load_warnings(chat_id)
    if target_user_id in warnings_data:
        del warnings_data[target_user_id]
        save_warnings(chat_id, warnings_data)
        await update.message.reply_text(f"✅ تم إزالة جميع التحذيرات عن {target_user_name}.")
    else:
        await update.message.reply_text("❗️ هذا المستخدم ليس لديه تحذيرات.")

async def warns(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type == "private":
        return await update.message.reply_text("❗️هذا الأمر يعمل فقط داخل المجموعات.")
    if not await is_admin(update, context):
        return await update.message.reply_text("🚫 هذا الأمر للمشرفين فقط.")
    chat_id = str(update.effective_chat.id)
    warnings_data = load_warnings(chat_id)
    if warnings_data:
        items = [
            f"- {data['name']} (تحذيرات: {data['count']}/3) (ID: {uid})"
            for uid, data in warnings_data.items()
        ]
        await update.message.reply_text("⚠️ قائمة المنبهين:\n" + "\n".join(items))
    else:
        await update.message.reply_text("✅ لا يوجد منبهون في هذه المجموعة حاليًا.")

async def delete_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type == "private":
        return await update.message.reply_text("❗️هذا الأمر يعمل فقط داخل المجموععات.")
    if not await is_admin(update, context):
        return await update.message.reply_text("🚫 هذا الأمر مخصص للمشرفين فقط.")
    if not update.message.reply_to_message:
        return await update.message.reply_text("❗️ يرجى الرد على رسالة لحذفها.")
    try:
        await context.bot.delete_message(update.effective_chat.id, update.message.reply_to_message.message_id)
        await update.message.delete()
    except Exception as e:
        await update.message.reply_text(f"❌ لم أتمكن من حذف الرسالة. الخطأ: {e}")

async def pin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type == "private":
        return await update.message.reply_text("❗️هذا الأمر يعمل فقط داخل المجموععات.")
    if not await is_admin(update, context):
        return await update.message.reply_text("🚫 هذا الأمر مخصص للمشرفين فقط.")
    if not update.message.reply_to_message:
        return await update.message.reply_text("❗️ يرجى الرد على رسالة لتثبيتها.")
    try:
        await context.bot.pin_chat_message(update.effective_chat.id, update.message.reply_to_message.message_id)
        await update.message.reply_text("✅ تم تثبيت الرسالة.")
    except Exception as e:
        await update.message.reply_text(f"❌ لم أتمكن من تثبيت الرسالة. الخطأ: {e}")

async def unpin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type == "private":
        return await update.message.reply_text("❗️هذا الأمر يعمل فقط داخل المجموععات.")
    if not await is_admin(update, context):
        return await update.message.reply_text("🚫 هذا الأمر مخصص للمشرفين فقط.")
    try:
        await context.bot.unpin_all_chat_messages(update.effective_chat.id)
        await update.message.reply_text("✅ تم إلغاء تثبيت جميع الرسائل.")
    except Exception as e:
        await update.message.reply_text(f"❌ لم أتمكن من إلغاء تثبيت الرسائل. الخطأ: {e}")

async def info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = None
    if update.message.reply_to_message:
        user = update.message.reply_to_message.from_user
    elif context.args and context.args[0].isdigit():
        try:
            member = await context.bot.get_chat_member(update.effective_chat.id, int(context.args[0]))
            user = member.user
        except:
            pass
    else:
        user = update.effective_user
    if user:
        info_text = (
            f"👤 الاسم: {user.full_name}\n"
            f"🆔 المعرف الرقمي: {user.id}\n"
            f"💬 اسم المستخدم: @{user.username or 'لا يوجد'}"
        )
        await update.message.reply_text(info_text)
    else:
        await update.message.reply_text("❗️ لم أتمكن من جلب معلومات المستخدم.")

# --- الردود العامة ---
def load_public_replies():
    if os.path.exists(PUBLIC_REPLIES_FILE):
        with open(PUBLIC_REPLIES_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_public_replies(data):
    with open(PUBLIC_REPLIES_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

async def publicreply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != DEVELOPER_ID:
        return await update.message.reply_text("🚫 هذا الأمر للمطور فقط.")
    if len(context.args) < 2:
        return await update.message.reply_text("❗️استخدم: /publicreply <الكلمة> <الرد>")
    keyword = context.args[0].strip().lower()
    response = " ".join(context.args[1:])
    replies = load_public_replies()
    if keyword in replies:
        if isinstance(replies[keyword], list):
            replies[keyword].append(response)
        else:
            replies[keyword] = [replies[keyword], response]
    else:
        replies[keyword] = response
    save_public_replies(replies)
    await update.message.reply_text(f"✅ تم إضافة رد عام للكلمة: {keyword}")

async def delpublicreply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != DEVELOPER_ID:
        return await update.message.reply_text("🚫 هذا الأمر للمطور فقط.")
    if not context.args:
        return await update.message.reply_text("❗️استخدم: /delpublicreply <الكلمة>")
    keyword = context.args[0].strip().lower()
    replies = load_public_replies()
    if keyword in replies:
        del replies[keyword]
        save_public_replies(replies)
        await update.message.reply_text(f"✅ تم حذف الرد العام للكلمة: {keyword}")
    else:
        await update.message.reply_text("❗️لا يوجد رد عام بهذه الكلمة.")

async def check_for_reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = str(update.effective_chat.id)
    replies = load_replies(chat_id)
    public_replies = load_public_replies()
    if not update.message or not update.message.text:
        return
    text = update.message.text.lower().strip()
    for keyword, response_list in replies.items():
        if text == keyword:
            await update.message.reply_text(
                random.choice(response_list) if isinstance(response_list, list) else response_list
            )
            return
    for keyword, response_list in public_replies.items():
        if text == keyword:
            await update.message.reply_text(
                random.choice(response_list) if isinstance(response_list, list) else response_list
            )
            return

async def main():
    # لتجنب مشاكل الحلقة في بيئات تفاعلية
    nest_asyncio.apply()

    TOKEN = "123456789:ABCDEFGabcdefg1234567890" #ضع token البوت المشغل
    application = ApplicationBuilder().token(TOKEN).build()

    # تسجيل الأوامر
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("mute", mute))
    application.add_handler(CommandHandler("unmute", unmute))
    application.add_handler(CommandHandler("mutes", mutes))
    application.add_handler(CommandHandler("ban", ban))
    application.add_handler(CommandHandler("unban", unban))
    application.add_handler(CommandHandler("bans", bans))
    application.add_handler(CommandHandler("warn", warn))
    application.add_handler(CommandHandler("unwarn", unwarn))
    application.add_handler(CommandHandler("warns", warns))
    application.add_handler(CommandHandler("del", delete_message))
    application.add_handler(CommandHandler("pin", pin))
    application.add_handler(CommandHandler("unpin", unpin))
    application.add_handler(CommandHandler("info", info))
    application.add_handler(CommandHandler("publicreply", publicreply))
    application.add_handler(CommandHandler("delpublicreply", delpublicreply))

    # الردود التلقائية
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, check_for_reply))

    # بدء الاستماع
    await application.run_polling()

if __name__ == "__main__":
    asyncio.run(main())