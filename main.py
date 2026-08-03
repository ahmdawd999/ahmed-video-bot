import os
import telebot
from telebot import types
import yt_dlp
from flask import Flask
from threading import Thread
import re
import random

# خادم ويب صغير لإبقاء البوت مستيقظاً
app = Flask('')

@app.route('/')
def home():
    return "البوت يعمل بنجاح 24/7!"

def run():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run)
    t.start()

# استدعاء التوكن
TOKEN = os.environ.get("BOT_TOKEN")
if not TOKEN:
    print("خطأ: لم يتم العثور على BOT_TOKEN")
    exit()

bot = telebot.TeleBot(TOKEN)

ADMIN_ID = 8460989245
USERS_FILE = "users.txt"
COOKIES_FILE = "cookies.txt"

# قائمة User-Agents متنوعة لتجنب الحظر
USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36',
    'Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1',
    'Mozilla/5.0 (Linux; Android 14; Pixel 7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36',
]

def get_random_ua():
    return random.choice(USER_AGENTS)

# حفظ المستخدمين
def save_user(chat_id):
    if not os.path.exists(USERS_FILE):
        with open(USERS_FILE, "w") as f:
            f.write("")
    with open(USERS_FILE, "r") as f:
        users = f.read().splitlines()
    if str(chat_id) not in users:
        with open(USERS_FILE, "a") as f:
            f.write(f"{chat_id}\n")

# تخزين المنصة المختارة
user_platform = {}
admin_state = {}

# أمر البداية
@bot.message_handler(commands=['start'])
def start_command(message):
    chat_id = message.chat.id
    user_platform[chat_id] = None
    admin_state[chat_id] = None
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

# لوحة تحكم المطور
@bot.message_handler(commands=['admin'])
def admin_command(message):
    chat_id = message.chat.id
    if chat_id != ADMIN_ID:
        return
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("📣 إرسال رسالة جماعية", callback_data="broadcast"))
    bot.send_message(chat_id, "مرحباً بك في لوحة تحكم المطور أحمد 🛠️", reply_markup=markup)

# استقبال الضغط على الأزرار
@bot.callback_query_handler(func=lambda call: True)
def check_callback(call):
    chat_id = call.message.chat.id
    
    if call.data == "broadcast":
        if chat_id != ADMIN_ID: return
        admin_state[chat_id] = "waiting_broadcast"
        bot.edit_message_text(chat_id=chat_id, message_id=call.message.message_id, 
                              text="📝 من فضلك أرسل نص الرسالة التي تريد إذاعتها لجميع المستخدمين:")
        return

    if call.data in ["yt", "ig", "fb", "tt"]:
        user_platform[chat_id] = call.data
        admin_state[chat_id] = None 
        platforms_names = {"yt": "🛑 يوتيوب", "ig": "📸 انستغرام", "fb": "📘 فيسبوك", "tt": "🖤 تيك توك"}
        name = platforms_names[call.data]
        bot.edit_message_text(chat_id=chat_id, message_id=call.message.message_id, 
                              text=f"لقد اخترت {name} 📥\n\n📍 من فضلك ارسل رابط المقطع الآن:")

# استقبال الإذاعة
@bot.message_handler(func=lambda msg: msg.chat.id == ADMIN_ID and admin_state.get(msg.chat.id) == "waiting_broadcast")
def handle_admin_broadcast(message):
    chat_id = message.chat.id
    admin_state[chat_id] = None
    broadcast_text = message.text
    
    if not os.path.exists(USERS_FILE):
        bot.send_message(chat_id, "❌ لا يوجد مستخدمين مسجلين.")
        return
        
    with open(USERS_FILE, "r") as f:
        users = f.read().splitlines()
        
    bot.send_message(chat_id, f"⏳ جاري الإرسال إلى {len(users)} مستخدم...")
    
    success = 0
    for user in users:
        try:
            bot.send_message(int(user), broadcast_text)
            success += 1
        except:
            pass
            
    bot.send_message(chat_id, f"✅ تم الإرسال بنجاح إلى {success} مستخدم")

# استقبال روابط التحميل
@bot.message_handler(func=lambda msg: user_platform.get(msg.chat.id) is not None)
def download_video(message):
    chat_id = message.chat.id
    url = message.text.strip()
    platform = user_platform[chat_id]
    
    if not url.startswith("http"):
        bot.send_message(chat_id, "⚠️ يرجى إرسال رابط صحيح يبدأ بـ http أو https.")
        return

    # معالجة روابط انستغرام
    if platform == "ig" and "instagram.com" in url:
        url = re.sub(r'\?.*$', '', url)
        if not url.endswith('/'):
            url += '/'
    
    status = bot.send_message(chat_id, "⏳ جاري التحميل... [0%]")
    
    def progress_hook(d):
        if d['status'] == 'downloading':
            total = d.get('total_bytes') or d.get('total_bytes_estimate')
            downloaded = d.get('downloaded_bytes', 0)
            if total and total > 0:
                percent = int((downloaded / total) * 100)
                if percent % 25 == 0:
                    try:
                        bot.edit_message_text(chat_id=chat_id, message_id=status.message_id, 
                                            text=f"⏳ جاري التحميل... [{percent}%]")
                    except:
                        pass
        elif d['status'] == 'finished':
            try:
                bot.edit_message_text(chat_id=chat_id, message_id=status.message_id, 
                                    text="⚡ اكتمل التحميل، جاري المعالجة...")
            except:
                pass

    # الإعدادات الأساسية
    ydl_opts = {
        'outtmpl': f'downloads/%(id)s.%(ext)s',
        'progress_hooks': [progress_hook],
        'quiet': True,
        'no_warnings': True,
        'extract_flat': False,
        'http_headers': {
            'User-Agent': get_random_ua(),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9,ar;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1',
            'Upgrade-Insecure-Requests': '1',
        },
        'socket_timeout': 30,
        'retries': 5,
        'fragment_retries': 5,
        'extractor_retries': 5,
    }

    # إعدادات المنصات
    if platform == "yt":
        ydl_opts.update({
            'format': 'bestvideo[ext=mp4][height<=1080]+bestaudio[ext=m4a]/best[ext=mp4][height<=1080]/best[height<=1080]',
            'merge_output_format': 'mp4',
        })
    elif platform == "ig":
        ydl_opts.update({
            'format': 'best[ext=mp4]/best',
            'extractor_args': {'instagram': {'embed': ['metadata']}},
        })
    elif platform in ["fb", "tt"]:
        ydl_opts.update({
            'format': 'best[ext=mp4]/best',
        })

    # إضافة الكوكيز إذا موجودة
    if os.path.exists(COOKIES_FILE) and os.path.getsize(COOKIES_FILE) > 0:
        ydl_opts['cookiefile'] = COOKIES_FILE

    # إنشاء مجلد التحميلات
    if not os.path.exists('downloads'):
        os.makedirs('downloads')

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            
            video_id = info.get('id', 'video')
            filename = None
            
            # البحث عن الملف المحمل
            for f in os.listdir('downloads'):
                if f.startswith(video_id) and f.endswith(('.mp4', '.mkv', '.webm')):
                    filename = os.path.join('downloads', f)
                    break
            
            if filename and os.path.exists(filename):
                file_size = os.path.getsize(filename)
                
                if file_size > 50 * 1024 * 1024:
                    bot.send_message(chat_id, "⚠️ حجم الفيديو كبير جداً (أكبر من 50MB)")
                    os.remove(filename)
                else:
                    try:
                        bot.edit_message_text(chat_id=chat_id, message_id=status.message_id, 
                                            text="📤 جاري رفع الفيديو...")
                    except:
                        pass
                    
                    with open(filename, 'rb') as vf:
                        bot.send_video(chat_id, vf, 
                                     caption="✅ تم التحميل بنجاح بواسطة بوت أحمد!",
                                     supports_streaming=True,
                                     timeout=60)
                    os.remove(filename)
            else:
                bot.send_message(chat_id, "❌ فشلت معالجة الفيديو - لم يتم العثور على الملف")
                
    except Exception as e:
        error_msg = str(e)
        print(f"Error: {error_msg}")
        
        if "Private video" in error_msg or "private" in error_msg.lower():
            bot.send_message(chat_id, "❌ هذا الفيديو خاص ولا يمكن تحميله")
        elif "Video unavailable" in error_msg:
            bot.send_message(chat_id, "❌ الفيديو غير متاح أو تم حذفه")
        elif "429" in error_msg or "Too Many Requests" in error_msg:
            bot.send_message(chat_id, "❌ تم حظر الطلب مؤقتاً، جرب:\n- إرسال رابط آخر\n- الانتظار 5 دقائق والمحاولة مرة أخرى")
        elif "Sign in" in error_msg or "login" in error_msg.lower():
            bot.send_message(chat_id, "❌ هذا المحتوى يتطلب تسجيل دخول. تأكد من إضافة ملف cookies.txt")
        else:
            bot.send_message(chat_id, "❌ فشل التحميل. تأكد من:\n- صحة الرابط\n- أن الحساب عام (للانستغرام)\n- حجم الفيديو أقل من 50MB")
    
    finally:
        user_platform[chat_id] = None
        try:
            bot.delete_message(chat_id, status.message_id)
        except:
            pass
        # تنظيف الملفات
        try:
            if os.path.exists('downloads'):
                for f in os.listdir('downloads'):
                    os.remove(os.path.join('downloads', f))
        except:
            pass

if __name__ == '__main__':
    keep_alive()
    print("البوت يعمل والويب سيرفر نشط...")
    bot.infinity_polling()
