import os
import telebot
from telebot import types
import yt_dlp

# توكن البوت الخاص بك
TOKEN = "8813772165:AAH4gHYpzZFFJIqPmRUz2diXFvCfhAElPSg"
bot = telebot.TeleBot(TOKEN)

# تخزين المنصة المختارة لكل مستخدم
user_platform = {}

# أمر البداية
@bot.message_handler(commands=['start'])
def start_command(message):
    chat_id = message.chat.id
    user_platform[chat_id] = None
    
    welcome_msg = "مرحبا بك في بوت احمد كيف يمكننا مساعده 🤝✨\n\n👇 يرجى اختيار المنصة المراد التحميل منها:"
    
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("🛑 يوتيوب", callback_data="yt"),
        types.InlineKeyboardButton("📸 انستا", callback_data="ig"),
        types.InlineKeyboardButton("📘 فيس", callback_data="fb"),
        types.InlineKeyboardButton("🖤 تيك توك", callback_data="tt")
    )
    bot.send_message(chat_id, welcome_msg, reply_markup=markup)

# استقبال الضغط على الأزرار
@bot.callback_query_handler(func=lambda call: call.data in ["yt", "ig", "fb", "tt"])
def check_button(call):
    chat_id = call.message.chat.id
    user_platform[chat_id] = call.data
    
    platforms_names = {"yt": "🛑 يوتيوب", "ig": "📸 انستغرام", "fb": "📘 فيسبوك", "tt": "🖤 تيك توك"}
    name = platforms_names[call.data]
    
    bot.edit_message_text(chat_id=chat_id, message_id=call.message.message_id, 
                          text=f"لقد اخترت {name} 📥\n\n📍 من فضلك ارسل رابط المقطع الآن لكي نقوم بتحميله بجودة عالية:")

# استقبال الرابط وتحميل الفيديو
@bot.message_handler(func=lambda msg: user_platform.get(msg.chat.id) is not None)
def download_video(message):
    chat_id = message.chat.id
    url = message.text.strip()
    
    if not url.startswith("http"):
        bot.send_message(chat_id, "⚠️ عذراً، يرجى إرسال رابط صحيح يبدأ بـ http أو https.")
        return

    # رسالة العداد المبدئية
    status = bot.send_message(chat_id, "⏳ جاري بدء التحميل والمعالجة... [0%]")
    
    # دالة تحديث العداد
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

    # إعدادات التحميل بالسيرفر لضمان السرعة والجودة المتوافقة مع تلغرام
    ydl_opts = {
        'format': 'best',
        'outtmpl': f'vid_{chat_id}.%(ext)s',
        'progress_hooks': [progress_hook],
        'quiet': True
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)
            
            if os.path.exists(filename):
                with open(filename, 'rb') as vf:
                    bot.send_video(chat_id, vf, caption="✅ تم تحميل الفيديو بنجاح بواسطة بوت أحمد!")
                os.remove(filename) # تنظيف السيرفر أولاً بأول لكي لا يتوقف البوت
            else:
                bot.send_message(chat_id, "❌ حدث خطأ، لم نتمكن من معالجة الفيديو.")
    except Exception as e:
        print(f"Error: {e}")
        bot.send_message(chat_id, "❌ عذراً، فشل تحميل الفيديو. تأكد من أن الرابط صحيح وحسابك عام وليس خاصاً.")
    finally:
        try: bot.delete_message(chat_id, status.message_id)
        except Exception: pass
        user_platform[chat_id] = None

# تشغيل مستمر
print("البوت يعمل...")
bot.infinity_polling()
