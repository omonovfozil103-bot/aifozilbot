import os
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from google import genai
from gtts import gTTS
import yt_dlp
# --- API KALITLAR VA SOZLAMALAR ---
TELEGRAM_BOT_TOKEN = "8993223013:AAEtU3w2CLtvvpnSXud-c2Xu4PLPxPsBxpI"
GEMINI_API_KEY = "AQ.Ab8RN6Jir4VIR1sge9ZG63HPyLa0_8aRuxpYmCoxAqIq7TBhAA"
ai_client = genai.Client(api_key=GEMINI_API_KEY)
logging.basicConfig(format="%(asctime)s - %(levelname)s - %(message)s", level=logging.INFO)
user_database = {}
def save_user_info(user):
    user_database[user.id] = {
        "id": user.id,
        "first_name": user.first_name or "Mavjud emas",
        "last_name": user.last_name or "",
        "username": f"@{user.username}" if user.username else "Mavjud emas",
        "is_bot": user.is_bot
    }

async def search_by_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    save_user_info(update.message.from_user)
    if not context.args:
        user = update.message.from_user
        uname = user.username if user.username else "Yo'q"
        text = (
            f"🆔 **Sizning Telegram ID'ingiz:** `{user.id}`\n"
            f"👤 **Ism:** {user.first_name}\n"
            f"🔗 **Username:** @{uname}\n\n"
            f"💡 *Boshqa odamni qidirish uchun: `/id 123456789` deb yozing.*"
        )
        await update.message.reply_text(text, parse_mode="Markdown")
        return

    search_id = context.args[0]
    if search_id.isdigit():
        target_id = int(search_id)
        if target_id in user_database:
            info = user_database[target_id]
            await update.message.reply_text(
                f"🔍 **Foydalanuvchi topildi:**\n\n"
                f"🆔 **ID:** `{info['id']}`\n"
                f"👤 **Ism:** {info['first_name']} {info['last_name']}\n"
                f"🔗 **Username:** {info['username']}\n"
                f"🔒 **Telefon raqami:** Yashiringan (Telegram maxfiylik siyosati)",
                parse_mode="Markdown"
            )
        else:
            await update.message.reply_text("❌ Bu ID ga ega foydalanuvchi hali botdan foydalanmagan.")
    else:
        await update.message.reply_text("❌ Iltimos, faqat raqamlardan iborat Telegram ID kiriting.")

async def handle_links(update: Update, context: ContextTypes.DEFAULT_TYPE):
    save_user_info(update.message.from_user)
    url = update.message.text
    social_platforms = ["instagram.com", "youtube.com", "youtu.be", "facebook.com", "fb.watch", "pinterest.com", "pin.it"]

    if any(platform in url for platform in social_platforms):
        msg = await update.message.reply_text("📥 Media yuklanmoqda, kuting...")
        ydl_opts = {'format': 'best', 'outtmpl': 'downloaded_media.%(ext)s', 'max_filesize': 50 * 1024 * 1024, 'quiet': True}

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])

            for file in os.listdir():
                if file.startswith("downloaded_media"):
                    if file.endswith(('.mp4', '.mov', '.mkv', '.webm')):
                        await update.message.reply_video(video=open(file, 'rb'), caption="✅ Video yuklab olindi!")
                    elif file.endswith(('.jpg', '.jpeg', '.png', '.webp')):
                        await update.message.reply_photo(photo=open(file, 'rb'), caption="✅ Rasm yuklab olindi!")
                    else:
                        await update.message.reply_document(document=open(file, 'rb'), caption="✅ Fayl yuklab olindi!")
                    os.remove(file)
                    break
            await msg.delete()
        except Exception as e:
            logging.error(f"Yuklashda xatolik: {e}")
            await msg.edit_text("❌ Mediani yuklab bo'lmadi.")

async def generate_image(update: Update, context: ContextTypes.DEFAULT_TYPE):
    save_user_info(update.message.from_user)
    prompt = " ".join(context.args)
    if not prompt:
        await update.message.reply_text("Rasm chizish uchun: `/draw chiroyli mashina` deb yozing.")
        return

    msg = await update.message.reply_text("🎨 Rasm chizilmoqda...")
    image_url = f"https://image.pollinations.ai/prompt/{prompt.replace(' ', '%20')}?width=1024&height=1024&nologo=true"
    await update.message.reply_photo(photo=image_url, caption=f"🖼 **Natija:** {prompt}")
    await msg.delete()

async def handle_text_and_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    save_user_info(update.message.from_user)
    user_text = update.message.text or update.message.caption or "Ushbu rasmni tushuntirib ber."

    try:
        response = ai_client.models.generate_content(model="gemini-1.5-flash", contents=user_text)
        ai_reply = response.text
    except Exception as e:
        ai_reply = "❌ AI javob bera olmadi."

    await update.message.reply_text(ai_reply)

async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    save_user_info(update.message.from_user)
    msg = await update.message.reply_text("🎙 Ovoz qayta ishlanmoqda...")

    voice_file = await context.bot.get_file(update.message.voice.file_id)
    await voice_file.download_to_drive("user_voice.ogg")
    audio_data = open("user_voice.ogg", "rb").read()

    response = ai_client.models.generate_content(
        model="gemini-1.5-flash",
        contents=["Foydalanuvchi ovozida nima dedi? Bunga o'zbek tilida qisqa va aniq javob ber.", {"mime_type": "audio/ogg", "data": audio_data}]
    )
    ai_text = response.text

    tts = gTTS(text=ai_text, lang='uz')
    tts.save("ai_response.mp3")

    await update.message.reply_voice(voice=open("ai_response.mp3", 'rb'), caption=f"📝 **Matn:** {ai_text}")

    os.remove("user_voice.ogg")
    os.remove("ai_response.mp3")
    await msg.delete()

def main():
    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    app.add_handler(CommandHandler("draw", generate_image))
    app.add_handler(CommandHandler("id", search_by_id))
    app.add_handler(MessageHandler(filters.Regex(r'https?://(www\.|m\.)?(instagram\.com|youtube\.com|youtu\.be|facebook\.com|fb\.watch|pinterest\.com|pin\.it)'), handle_links))
    app.add_handler(MessageHandler(filters.VOICE, handle_voice))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_and_photo))

    print("Bot muvaffaqiyatli ishga tushdi!")
    app.run_polling()

if __name__ == "__main__":
    main()
