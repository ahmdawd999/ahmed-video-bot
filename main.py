import os
import telebot
from telebot import types
import yt_dlp
from flask import Flask
from threading import Thread

# خادم ويب صغير لإبقاء البوت مستيقظاً على السيرفر المجاني
app = Flask('')

@app.route('/')
def home():
    return "البوت يعمل بنجاح 24/7!"

def run():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run)
    t.start()

# استدعاء التوكن بشكل آمن من إعدادات السيرفر
TOKEN = os.environ.get("BOT_TOKEN")
bot = telebot.TeleBot(TOKEN)

# 🛠️ معرف حساب المطور أحمد لفتح لوحة التحكم
ADMIN_ID = 8460989245  

# اسم ملف حفظ المستخدمين
USERS_FILE = "users.txt"

# دالة لحفظ المستخدم الجديد
def save_user(chat_id):
    if not os.path.exists(USERS_FILE):
        with open(USERS_FILE, "w") as f:
            f.write("")
            
    with open(USERS_FILE, "r") as f:
        users = f.read().splitlines()
        
    if str(chat_id) not in users:
        with open(USERS_FILE, "a") as f:
            f.write(f"{chat_id}\n")

# تخزين المنصة المختارة لكل مستخدم
user_platform = {}
admin_state = {}

# أمر البداية
@bot.message_handler(commands=['start'])
def start_command(message):
    chat_id = message.chat.id
    user_platform[chat_id] = None
    admin_state[chat_id] = None
    
    # حفظ المستخدم في القائمة
    save_user(chat_id)
    
    welcome_msg = "مرحبا بك في بوت احمد كيف يمكننا مساعده 🤝✨\n\n👇 يرجى اختيار المنصة المراد التحميل منها:"
    
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("🛑 يوتيوب", callback_data="yt"),
        types.InlineKeyboardButton("📸 انستا", callback_data="ig"),
        types.InlineKeyboardButton("📘 فيس", callback_data="fb"),
        types.InlineKeyboardButton("🖤 تيك توك", callback_data="tt")
    )
    bot.send_message(chat_id, welcome_msg, reply_markup=markup)

# ⚙️ أمر لوحة التحكم للمطور لإرسال رسائل جماعية
@bot.message_handler(commands=['admin'])
def admin_command(message):
    chat_id = message.chat.id
    if chat_id != ADMIN_ID:
        return
        
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("📣 إرسال رسالة جماعية (إذاعة)", callback_data="broadcast"))
    bot.send_message(chat_id, "مرحباً بك في لوحة تحكم المطور أحمد 🛠️", reply_markup=markup)

# استقبال الضغط على الأزرار
@bot.callback_query_handler(func=lambda call: True)
def check_callback(call):
    chat_id = call.message.chat.id
    
    # التعامل مع أزرار لوحة التحكم
    if call.data == "broadcast":
        if chat_id != ADMIN_ID: return
        admin_state[chat_id] = "waiting_broadcast"
        bot.edit_message_text(chat_id=chat_id, message_id=call.message.message_id, 
                              text="📝 من فضلك أرسل نص الرسالة التي تريد إذاعتها لجميع المستخدمين الآن:")
        return

    # التعامل مع أزرار منصات التحميل
    if call.data in ["yt", "ig", "fb", "tt"]:
        user_platform[chat_id] = call.data
        admin_state[chat_id] = None 
        platforms_names = {"yt": "🛑 يوتيوب", "ig": "📸 انستغرام", "fb": "📘 فيسبوك", "tt": "🖤 تيك توك"}
        name = platforms_names[call.data]
        bot.edit_message_text(chat_id=chat_id, message_id=call.message.message_id, 
                              text=f"لقد اخترت {name} 📥\n\n📍 من فضلك ارسل رابط المقطع الآن لكي نقوم بتحميله بجودة عالية:")

# استقبال نص الإذاعة من الأدمن حصراً
@bot.message_handler(func=lambda msg: msg.chat.id == ADMIN_ID and admin_state.get(msg.chat.id) == "waiting_broadcast")
def handle_admin_broadcast(message):
    chat_id = message.chat.id
    admin_state[chat_id] = None
    broadcast_text = message.text
    
    if not os.path.exists(USERS_FILE):
        bot.send_message(chat_id, "❌ لا يوجد مستخدمين مسجلين بعد في البوت.")
        return
        
    with open(USERS_FILE, "r") as f:
        users = f.read().splitlines()
        
    bot.send_message(chat_id, f"⏳ جاري بدء الإرسال إلى {len(users)} مستخدم...")
    
    success = 0
    failed = 0
    for user in users:
        try:
            bot.send_message(int(user), broadcast_text)
            success += 1
        except Exception:
            failed += 1 
            
    bot.send_message(chat_id, f"✅ تم انتهاء الإذاعة بنجاح!\n\n🟢 تم الإرسال إلى: {success}\n🔴 فشل الإرسال إلى: {failed} (قاموا بحظر البوت)")

# استقبال روابط التحميل من المستخدمين بناءً على المنصة المختارة
@bot.message_handler(func=lambda msg: user_platform.get(msg.chat.id) is not None)
def download_video(message):
    chat_id = message.chat.id
    url = message.text.strip()
    
    if not url.startswith("http"):
        bot.send_message(chat_id, "⚠️ عذراً، يرجى إرسال رابط صحيح يبدأ بـ http أو https.")
        return

    status = bot.send_message(chat_id, "⏳ جاري بدء التحميل والمعالجة... [0%]")
    
    def progress_hook(d):
        if d['status'] == 'downloading':
            total = d.get('total_bytes') or d.get('total_bytes_estimate')
            downloaded = d.get('downloaded_bytes', 0)
            if total:
                percent = int((downloaded / total) * 100)
                try:
                    if percent % 20 == 0:
                        bot.edit_message_text(chat_id=chat_id, message_id=status.message_id, text=f"⏳ جاري تحميل ومعالجة المقطع... [{percent}%]")
                except Exception: pass
        elif d['status'] == 'finished':
            try: bot.edit_message_text(chat_id=chat_id, message_id=status.message_id, text="⚡ تم اكتمال التحميل، جاري إرسال الفيديو...")
            except Exception: pass

    # 🌟 إعدادات ذكية جداً ومدمجة لتخطي حظر يوتيوب الحديث على السيرفرات السحابية
    ydl_opts = {
        'format': 'best[ext=mp4]/best', 
        'outtmpl': f'vid_{chat_id}.%(ext)s',
        'progress_hooks': [progress_hook],
        'quiet': True,
        'extractor_args': {
            'youtube': {
                'player_client': ['ios', 'android'], # استخدام محاكاة الهواتف الذكية لأنها الأقل حظراً
                'skip': ['webpage']
            }
        },
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 16_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.5 Mobile/15E148 Safari/604.1'
        }
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)
            
            if os.path.exists(filename):
                with open(filename, 'rb') as vf:
                    bot.send_video(chat_id, vf, caption="✅ تم تحميل الفيديو بنجاح بواسطة بوت أحمد!")
                os.remove(filename) 
            else:
                bot.send_message(chat_id, "❌ حدث خطأ، لم نتمكن من معالجة الفيديو.")
    except Exception as e:
        print(f"Error: {e}")
        bot.send_message(chat_id, "❌ عذراً، فشل تحميل الفيديو. تأكد من أن الرابط صحيح وحسابك عام وليس خاصاً.")
    finally:
        try: bot.delete_message(chat_id, status.message_id)
        except Exception: pass
        user_platform[chat_id] = None

# تشغيل البوت والويب سيرفر معاً
if __name__ == '__main__':
    keep_alive()
    print("البوت يعمل والويب سيرفر نشط...")
    bot.infinity_polling()
