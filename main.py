import nest_asyncio
import logging
import json
import os
import random
import asyncio
from telegram import Update, ChatPermissions, BotCommand
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    ContextTypes, filters, ConversationHandler
)

logging.basicConfig(level=logging.INFO)

REPLIES_FILE = "replies.json"
WARNINGS_FILE = "warnings.json"
CHAT_IDS_FILE = "chat_ids.json"
BANNED_USERS_FILE = "banned_users.json"

DEVELOPER_ID = XXXXXXXXXX #عنوان ID الخاص بك كمطور

# --- وظائف التحميل والحفظ ---
def load_replies():
    if os.path.exists(REPLIES_FILE):
        with open(REPLIES_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_replies(data):
    with open(REPLIES_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def load_warnings():
    if os.path.exists(WARNINGS_FILE):
        with open(WARNINGS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_warnings(data):
    with open(WARNINGS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def load_chat_ids():
    if os.path.exists(CHAT_IDS_FILE):
        with open(CHAT_IDS_FILE, "r") as f:
            return json.load(f)
    return []

def save_chat_ids(data):
    with open(CHAT_IDS_FILE, "w") as f:
        json.dump(data, f)

def load_banned_users():
    if os.path.exists(BANNED_USERS_FILE):
        with open(BANNED_USERS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_banned_users(data):
    with open(BANNED_USERS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

replies = load_replies()
warnings_data = load_warnings()
chat_ids = load_chat_ids()
banned_users_data = load_banned_users()

# --- الدوال المساعدة ---
async def is_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type == "private":
        return False
    member = await context.bot.get_chat_member(update.effective_chat.id, update.effective_user.id)
    return member.status in ['administrator', 'creator']

async def get_target_user_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = None
    # إذا كانت الرسالة ردًا
    if update.message.reply_to_message:
        user_id = update.message.reply_to_message.from_user.id
    # إذا كان هناك وسيط رقمي (معرّف)
    elif context.args and context.args[0].isdigit():
        user_id = int(context.args[0])
    # إذا كانت الرسالة النصية نفسها تحتوي على user_id (مثلاً 'حظر 12345')
    elif update.message.text:
        parts = update.message.text.split()
        # نتحقق من وجود جزء ثانٍ بعد الأمر النصي ومحاولة تحويله إلى رقم
        if len(parts) > 1 and parts[1].isdigit():
            user_id = int(parts[1])
    return user_id

# --- جميع دوال الأوامر ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    cid = update.effective_chat.id
    if cid not in chat_ids:
        chat_ids.append(cid)
        save_chat_ids(chat_ids)
    await update.message.reply_text("يا مرحبا... معاك يوريتشي مدير المجموعات")

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
    
    try:
        await context.bot.restrict_chat_member(update.effective_chat.id, user_id, permissions=ChatPermissions(can_send_messages=False))
        await update.message.reply_text("✅ تم كتم المستخدم.")
    except Exception as e:
        await update.message.reply_text(f"❌ لم أتمكن من كتم المستخدم. تأكد أنني مشرف ولدي الصلاحيات الكافية. الخطأ: {e}")


async def unmute(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type == "private":
        return await update.message.reply_text("❗️هذا الأمر يعمل فقط داخل المجموعات.")
    if not await is_admin(update, context):
        return await update.message.reply_text("🚫 هذا الأمر للمشرفين فقط.")
    user_id = await get_target_user_id(update, context)
    if not user_id:
        return await update.message.reply_text("❗️ يرجى الرد على رسالة أو تزويدي بالمعرّف الرقمي للمستخدم.")
    
    try:
        await context.bot.restrict_chat_member(update.effective_chat.id, user_id, permissions=ChatPermissions(can_send_messages=True))
        await update.message.reply_text("✅ تم فك الكتم.")
    except Exception as e:
        await update.message.reply_text(f"❌ لم أتمكن من فك كتم المستخدم. الخطأ: {e}")

async def mutes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # دالة mutes المفقودة
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
    
    chat_id = str(update.effective_chat.id)
    user_name = f"Unknown User ({user_id})" # قيمة افتراضية
    try:
        # محاولة جلب الاسم لتخزينه
        member = await context.bot.get_chat_member(update.effective_chat.id, user_id)
        user_name = member.user.full_name
    except Exception:
        pass # إذا فشل جلب الاسم، نستخدم القيمة الافتراضية

    try:
        await context.bot.ban_chat_member(update.effective_chat.id, user_id)
        # حفظ المستخدم المحظور بعد التأكد من الحظر
        banned_users_data.setdefault(chat_id, {})[str(user_id)] = user_name
        save_banned_users(banned_users_data)
        await update.message.reply_text("🚫 تم حظر المستخدم.")
    except Exception as e:
        await update.message.reply_text(f"❌ لم أتمكن من حظر المستخدم. تأكد أنني مشرف ولدي الصلاحيات الكافية. الخطأ: {e}")


async def unban(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type == "private":
        return await update.message.reply_text("❗️هذا الأمر يعمل فقط داخل المجموعات.")
    if not await is_admin(update, context):
        return await update.message.reply_text("🚫 هذا الأمر للمشرفين فقط.")
    user_id = await get_target_user_id(update, context)
    if not user_id:
        return await update.message.reply_text("❗️ يرجى الرد على رسالة أو تزويدي بالمعرّف الرقمي للمستخدم.")
    
    chat_id = str(update.effective_chat.id)
    try:
        await context.bot.unban_chat_member(update.effective_chat.id, user_id)
        # إزالة المستخدم من قائمة المحظورين الداخلية عند رفع الحظر
        if chat_id in banned_users_data and str(user_id) in banned_users_data[chat_id]:
            del banned_users_data[chat_id][str(user_id)]
            save_banned_users(banned_users_data)
        await update.message.reply_text("✅ تم رفع الحظر.")
    except Exception as e:
        await update.message.reply_text(f"❌ لم أتمكن من رفع الحظر عن المستخدم. الخطأ: {e}")


async def bans(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type == "private":
        return await update.message.reply_text("❗️هذا الأمر يعمل فقط داخل المجموعات.")
    if not await is_admin(update, context):
        return await update.message.reply_text("🚫 هذا الأمر للمشرفين فقط.")
    
    chat_id = str(update.effective_chat.id)
    if chat_id in banned_users_data and banned_users_data[chat_id]:
        banned_list = "\n".join([f"- {name} (ID: {uid})" for uid, name in banned_users_data[chat_id].items()])
        await update.message.reply_text(f"🚫 قائمة المحظورين في هذه المجموعة:\n{banned_list}")
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
        except Exception:
            target_user_name = f"Unknown User ({target_user_id})"
    else:
        return await update.message.reply_text("❗️ يجب الرد على رسالة المستخدم أو تزويدي بمعرفه الرقمي.")

    chat_id = str(update.effective_chat.id)
    warnings_data.setdefault(chat_id, {}).setdefault(target_user_id, {"count": 0, "name": target_user_name})
    warnings_data[chat_id][target_user_id]["count"] += 1
    warnings_data[chat_id][target_user_id]["name"] = target_user_name # تحديث الاسم في حال تغير
    save_warnings(warnings_data)

    if warnings_data[chat_id][target_user_id]["count"] >= 3:
        try:
            await context.bot.ban_chat_member(chat_id=update.effective_chat.id, user_id=int(target_user_id))
            # إضافة المستخدم إلى قائمة المحظورين الداخلية عند الحظر بسبب التحذيرات
            banned_users_data.setdefault(chat_id, {})[target_user_id] = target_user_name
            save_banned_users(banned_users_data)

            del warnings_data[chat_id][target_user_id]
            save_warnings(warnings_data)
            await update.message.reply_text(f"🚫 {target_user_name} تم حظره بعد 3 تحذيرات.")
        except Exception as e:
            await update.message.reply_text(f"❌ حدث خطأ أثناء محاولة حظر {target_user_name}: {e}")
    else:
        await update.message.reply_text(f"⚠️ تم تحذير {target_user_name} ({warnings_data[chat_id][target_user_id]['count']}/3)")

async def warns(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type == "private":
        return await update.message.reply_text("❗️هذا الأمر يعمل فقط داخل المجموعات.")
    if not await is_admin(update, context):
        return await update.message.reply_text("🚫 هذا الأمر للمشرفين فقط.")
    
    chat_id = str(update.effective_chat.id)
    if chat_id in warnings_data and warnings_data[chat_id]:
        warned_list_items = []
        for uid, data in warnings_data[chat_id].items():
            warned_list_items.append(f"- {data['name']} (تحذيرات: {data['count']}/3) (ID: {uid})")
        warned_list = "\n".join(warned_list_items)
        await update.message.reply_text(f"⚠️ قائمة المنبهين في هذه المجموعة:\n{warned_list}")
    else:
        await update.message.reply_text("✅ لا يوجد منبهون في هذه المجموعة حاليًا.")

async def delete_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type == "private":
        return await update.message.reply_text("❗️هذا الأمر يعمل فقط داخل المجموعات.")
    if not await is_admin(update, context):
        return await update.message.reply_text("🚫 هذا الأمر مخصص للمشرفين فقط.")
    if not update.message.reply_to_message:
        return await update.message.reply_text("❗️ يرجى الرد على رسالة لحذفها.")
    try:
        await context.bot.delete_message(update.effective_chat.id, update.message.reply_to_message.message_id)
        # يمكنك حذف رسالة الأمر أيضاً إذا أردت
        await update.message.delete()
    except Exception as e:
        await update.message.reply_text(f"❌ لم أتمكن من حذف الرسالة. تأكد أنني مشرف ولدي صلاحية حذف الرسائل. الخطأ: {e}")
    # لا ترسل رسالة "تم حذف الرسالة" لتجنب ظهورها ثم اختفائها إذا حذفت رسالة الأمر

async def pin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type == "private":
        return await update.message.reply_text("❗️هذا الأمر يعمل فقط داخل المجموعات.")
    if not await is_admin(update, context):
        return await update.message.reply_text("🚫 هذا الأمر مخصص للمشرفين فقط.")
    if update.message.reply_to_message:
        try:
            await context.bot.pin_chat_message(update.effective_chat.id, update.message.reply_to_message.message_id)
            await update.message.reply_text("✅ تم تثبيت الرسالة.")
        except Exception as e:
            await update.message.reply_text(f"❌ لم أتمكن من تثبيت الرسالة. تأكد أنني مشرف ولدي صلاحية التثبيت. الخطأ: {e}")
    else:
        await update.message.reply_text("❗️ يرجى الرد على رسالة لتثبيتها.")


async def unpin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type == "private":
        return await update.message.reply_text("❗️هذا الأمر يعمل فقط داخل المجموعات.")
    if not await is_admin(update, context):
        return await update.message.reply_text("🚫 هذا الأمر مخصص للمشرفين فقط.")
    try:
        await context.bot.unpin_all_chat_messages(update.effective_chat.id)
        await update.message.reply_text("✅ تم إلغاء تثبيت كل الرسائل.")
    except Exception as e:
        await update.message.reply_text(f"❌ لم أتمكن من إلغاء تثبيت الرسائل. تأكد أنني مشرف ولدي صلاحية إلغاء التثبيت. الخطأ: {e}")

async def info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = None
    if update.message.reply_to_message:
        user = update.message.reply_to_message.from_user
    elif context.args and context.args[0].isdigit():
        user_id = int(context.args[0])
        try:
            member = await context.bot.get_chat_member(update.effective_chat.id, user_id)
            user = member.user
        except Exception:
            await update.message.reply_text(f"❌ لم أتمكن من العثور على المستخدم بالمعرّف الرقمي: {user_id}")
            return
    else:
        user = update.effective_user

    if user:
        await update.message.reply_text(
            f"👤 معلومات المستخدم:\n\n- الاسم: {user.full_name}\n- المعرف: @{user.username if user.username else 'لا يوجد'}\n- المعرف الرقمي: {user.id}"
        )
    else:
        await update.message.reply_text("❗️ يرجى الرد على رسالة أو تزويدي بالمعرّف الرقمي للمستخدم.")


ADD_KEYWORD, ADD_RESPONSE = range(2)
DEL_KEYWORD = 3

async def addreply_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type == "private":
        return await update.message.reply_text("❗️هذا الأمر يعمل فقط داخل المجموعات.")
    if not await is_admin(update, context):
        return await update.message.reply_text("🚫 هذا الأمر للمشرفين فقط.")
    await update.message.reply_text("📝 أرسل الكلمة المفتاحية:")
    return ADD_KEYWORD

async def addreply_keyword(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["keyword"] = update.message.text.lower()
    await update.message.reply_text("💬 أرسل الرد المراد استخدامه:")
    return ADD_RESPONSE

async def addreply_response(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyword = context.user_data["keyword"]
    response = update.message.text
    if keyword in replies:
        if isinstance(replies[keyword], list):
            replies[keyword].append(response)
        else:
            replies[keyword] = [replies[keyword], response]
    else:
        replies[keyword] = [response]
    save_replies(replies)
    await update.message.reply_text(f"✅ تم حفظ الرد `{keyword}`", parse_mode="Markdown")
    context.user_data.pop("keyword", None) # إزالة الكلمة المفتاحية بعد الاستخدام
    return ConversationHandler.END

# --- وظائف ConversationHandler لـ delreply ---
async def delreply_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type == "private":
        return await update.message.reply_text("❗️هذا الأمر يعمل فقط داخل المجموعات.")
    if not await is_admin(update, context):
        return await update.message.reply_text("🚫 هذا الأمر للمشرفين فقط.")
    await update.message.reply_text("📝 أرسل الكلمة المفتاحية للرد الذي تريد حذفه:")
    return DEL_KEYWORD

async def delreply_process_keyword(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyword = update.message.text.lower()
    if keyword in replies:
        del replies[keyword]
        save_replies(replies)
        await update.message.reply_text(f"🗑️ تم حذف الرد `{keyword}`", parse_mode="Markdown")
    else:
        await update.message.reply_text(f"⚠️ لا يوجد رد بهذه الكلمة: `{keyword}`", parse_mode="Markdown")
    return ConversationHandler.END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear() # مسح أي بيانات سابقة
    await update.message.reply_text("🚫 تم إلغاء العملية.")
    return ConversationHandler.END

async def check_for_reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # هذه الدالة الآن تركز بشكل أكبر على الردود التلقائية العادية
    # لأن معظم الأوامر النصية تم التعامل معها بـ MessageHandler صريح
    
    text = update.message.text.lower().strip()
    
    # فحص الردود التلقائية العادية
    for keyword, response_list in replies.items():
        if text == keyword: # التأكد من المطابقة التامة للكلمة المفتاحية
            if isinstance(response_list, list):
                await update.message.reply_text(random.choice(response_list))
            else:
                await update.message.reply_text(response_list)
            return # إنهاء الدالة بعد إرسال الرد

async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != DEVELOPER_ID:
        await update.message.reply_text("⛔ هذا الأمر مقصور على المطور فقط!")
        return

    if not context.args and not update.message.reply_to_message:
        await update.message.reply_text("📌 استخدام الأمر:\n/broadcast <النص>\nأو بالرد على رسالة (نص/ملف/صورة)")
        return

    stats = {
        'total': len(chat_ids),
        'success': 0,
        'failed': 0,
        'pinned': 0,
        'pin_failed': 0,
        'failed_chats': []
    }

    for cid in chat_ids:
        try:
            # إرسال الرسالة
            if update.message.reply_to_message:
                msg = await context.bot.forward_message(
                    chat_id=cid,
                    from_chat_id=update.effective_chat.id,
                    message_id=update.message.reply_to_message.message_id
                )
            else:
                msg = await context.bot.send_message(
                    chat_id=cid,
                    text=" ".join(context.args)
                )
            
            # تثبيت الرسالة في المجموعات فقط
            if not msg.chat.type == "private":
                try:
                    await context.bot.pin_chat_message(chat_id=cid, message_id=msg.message_id)
                    stats['pinned'] += 1
                except Exception as pin_error:
                    stats['pin_failed'] += 1
                    logging.warning(f"تعذر تثبيت الرسالة في {cid}: {pin_error}")
            
            stats['success'] += 1
        except Exception as e:
            stats['failed'] += 1
            stats['failed_chats'].append(cid)
            logging.error(f"فشل الإرسال إلى {cid}: {e}")

    # إرسال التقرير
    report = (
        f"📊 تقرير الإذاعة:\n"
        f"• عدد الدردشات المستهدفة: {stats['total']}\n"
        f"• نجح الإرسال إلى: {stats['success']} دردشة\n"
        f"• فشل الإرسال إلى: {stats['failed']} دردشة\n"
        f"• تم تثبيت الرسالة في: {stats['pinned']} دردشة\n"
        f"• فشل التثبيت في: {stats['pin_failed']} دردشة\n"
    )
    
    if stats['failed_chats']:
        report += f"🔴 الدردشات الفاشلة:\n" + "\n".join(map(str, stats['failed_chats'][:5]))
        if len(stats['failed_chats']) > 5:
            report += f"\n...و{len(stats['failed_chats']) - 5} أخرى"

    await context.bot.send_message(chat_id=DEVELOPER_ID, text=report)
    await update.message.reply_text("✅ تمت الإذاعة والتثبيت! التقرير أرسل إليك.")

# --- إعداد الأوامر ---
async def set_commands(app):
    commands = [
        BotCommand("start", "بدء البوت"),
        BotCommand("help", "عرض قائمة الأوامر"),
        BotCommand("mute", "كتم المستخدم"),
        BotCommand("unmute", "فك الكتم"),
        BotCommand("mutes", "عرض المكتومين"),
        BotCommand("ban", "حظر المستخدم"),
        BotCommand("unban", "رفع الحظر"),
        BotCommand("bans", "عرض المحظورين"),
        BotCommand("warn", "تحذير المستخدم"),
        BotCommand("warns", "عرض المنبهين"),
        BotCommand("del", "حذف رسالة"),
        BotCommand("pin", "تثبيت رسالة"),
        BotCommand("unpin", "إلغاء تثبيت جميع الرسائل"),
        BotCommand("info", "عرض معلومات المستخدم"),
        BotCommand("addreply", "إضافة رد تلقائي"),
        BotCommand("delreply", "حذف رد تلقائي"),
        BotCommand("cancel", "إلغاء العملية"),
        BotCommand("broadcast", "إذاعة وتثبيت للمطور")
    ]
    await app.bot.set_my_commands(commands)

# --- الدالة الرئيسية ---
async def main():
    TOKEN = "XXXXXXXXXX:XXXXXXXXXXX-X-XXXXXXXXXXXXXXXXXXXX" #عنوان token الخاص بالبوت
    app = ApplicationBuilder().token(TOKEN).build()

    # Handlers for slash commands
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("mute", mute))
    app.add_handler(CommandHandler("unmute", unmute))
    app.add_handler(CommandHandler("ban", ban))
    app.add_handler(CommandHandler("unban", unban))
    app.add_handler(CommandHandler("warn", warn))
    app.add_handler(CommandHandler("del", delete_message))
    app.add_handler(CommandHandler("info", info))
    app.add_handler(CommandHandler("mutes", mutes)) # تم التأكد من وجود هذه الدالة الآن
    app.add_handler(CommandHandler("pin", pin))
    app.add_handler(CommandHandler("unpin", unpin))
    app.add_handler(CommandHandler("broadcast", broadcast))
    app.add_handler(CommandHandler("bans", bans))
    app.add_handler(CommandHandler("warns", warns))

    # Conversation handler for addreply (slash and text)
    addreply_handler = ConversationHandler(
        entry_points=[
            CommandHandler("addreply", addreply_start),
            MessageHandler(filters.Regex(r"^إضافة رد$"), addreply_start)
        ],
        states={
            ADD_KEYWORD: [MessageHandler(filters.TEXT & ~filters.COMMAND, addreply_keyword)],
            ADD_RESPONSE: [MessageHandler(filters.TEXT & ~filters.COMMAND, addreply_response)],
        },
        fallbacks=[CommandHandler("cancel", cancel), MessageHandler(filters.Regex(r"^إلغاء$"), cancel)],
    )
    app.add_handler(addreply_handler)

    # Conversation handler for delreply (slash and text)
    delreply_handler = ConversationHandler(
        entry_points=[
            CommandHandler("delreply", delreply_start),
            MessageHandler(filters.Regex(r"^حذف رد$"), delreply_start)
        ],
        states={
            DEL_KEYWORD: [MessageHandler(filters.TEXT & ~filters.COMMAND, delreply_process_keyword)],
        },
        fallbacks=[CommandHandler("cancel", cancel), MessageHandler(filters.Regex(r"^إلغاء$"), cancel)],
    )
    app.add_handler(delreply_handler)

    # Handlers for specific text-based commands (direct mapping)
    # هذه يجب أن تكون قبل check_for_reply لتلقي الأولوية
    app.add_handler(MessageHandler(filters.Regex(r"^الاوامر$"), help_command))
    app.add_handler(MessageHandler(filters.Regex(r"^كتم$"), mute))
    app.add_handler(MessageHandler(filters.Regex(r"^فك كتم$"), unmute))
    app.add_handler(MessageHandler(filters.Regex(r"^المكتومين$"), mutes))
    app.add_handler(MessageHandler(filters.Regex(r"^حظر$"), ban))
    app.add_handler(MessageHandler(filters.Regex(r"^فك حظر$"), unban))
    app.add_handler(MessageHandler(filters.Regex(r"^المحظورين$"), bans))
    app.add_handler(MessageHandler(filters.Regex(r"^تحذير$"), warn))
    app.add_handler(MessageHandler(filters.Regex(r"^المنبهين$"), warns))
    app.add_handler(MessageHandler(filters.Regex(r"^حذف$"), delete_message))
    app.add_handler(MessageHandler(filters.Regex(r"^تثبيت$"), pin))
    app.add_handler(MessageHandler(filters.Regex(r"^إلغاء تثبيت$"), unpin))
    app.add_handler(MessageHandler(filters.Regex(r"^معلومات$"), info))
    
    # Fallback for general text messages (for auto-replies)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, check_for_reply))


    await set_commands(app)
    print("✅ البوت يعمل الآن...")
    await app.run_polling()

if __name__ == "__main__":
    nest_asyncio.apply()
    asyncio.get_event_loop().run_until_complete(main())
