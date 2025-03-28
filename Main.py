import telebot
from telebot import types
import yt_dlp
import os
from threading import Thread
from youtube_search import YoutubeSearch

BOT_TOKEN = 'token giriniz buraya/token here'
bot = telebot.TeleBot(BOT_TOKEN)

ydl_opts = {
    'format': 'bestaudio[ext=mp3]/bestaudio',
    'outtmpl': 'downloads/%(title)s.%(ext)s',
    'noplaylist': True,
    'quiet': True,
    'no_warnings': True,
}

def search_youtube(query, max_results=8):
    return YoutubeSearch(query, max_results=max_results).to_dict()

def download_audio(url, chat_id, message_id):
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)
            if os.path.getsize(filename) > 50 * 1024 * 1024:
                bot.edit_message_text(chat_id=chat_id, message_id=message_id, text="❌ Dosya boyutu 50MB limitini aşıyor.")
                os.remove(filename)
                return
            with open(filename, 'rb') as audio:
                bot.send_audio(chat_id=chat_id, audio=audio, title=info.get('title', 'Bilinmeyen Başlık'), performer=info.get('uploader', 'Bilinmeyen Sanatçı'))
            bot.edit_message_text(chat_id=chat_id, message_id=message_id, text="✅ İndirme tamamlandı. Keyfini çıkarın!")
            os.remove(filename)
    except Exception as e:
        bot.edit_message_text(chat_id=chat_id, message_id=message_id, text=f"❌ Hata oluştu: {str(e)}")

@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, (
        "Merhaba!\n"
        "Size YouTube üzerinden müzik indirme konusunda yardımcı olacağım.\n\n"
        "Lütfen aşağıdaki seçeneklerden birini kullanın:\n"
        "🎵 Şarkı veya sanatçı adını yazın\n"
        "🔗 YouTube bağlantısı paylaşın\n"
        "✨ Satır içi arama için @BotAdınızı kullanın\n\n"
        "Hızlı ve kaliteli bir şekilde müziğinizi size ulaştıracağım.\n"
        "Developed by <a href='https://github.com/prymx'>prymx</a> | Telegram: <a href='https://t.me/prymx_xd'>@prymx_xd</a>"
    ), parse_mode='HTML')

@bot.message_handler(content_types=['text'])
def handle_text(message):
    query = message.text.strip()
    chat_id = message.chat.id
    
    if 'youtube.com' in query.lower() or 'youtu.be' in query.lower():
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("İndir", callback_data=f"download_{query}"))
        status_message = bot.reply_to(message, "YouTube bağlantısı tespit edildi. İndirmek için tıklayın:", reply_markup=markup)
        bot.chat_data = {'message_id': status_message.message_id}
    else:
        results = search_youtube(query)
        if not results:
            bot.reply_to(message, "Maalesef aradığınız şarkı bulunamadı. Lütfen başka bir terim deneyin.")
            return
        
        markup = types.InlineKeyboardMarkup()
        for i, result in enumerate(results, 1):
            title = result['title'][:40] + "..." if len(result['title']) > 40 else result['title']
            url = f"https://www.youtube.com/watch?v={result['id']}"
            markup.add(types.InlineKeyboardButton(f"{i}. {title}", callback_data=f"download_{url}"))
        markup.add(types.InlineKeyboardButton("Daha Fazlası", callback_data=f"more_{query}_8"))
        
        status_message = bot.reply_to(message, f"'{query}' için bulunan sonuçlar:", reply_markup=markup)
        bot.chat_data = {'message_id': status_message.message_id}

@bot.inline_handler(lambda query: len(query.query) > 0)
def inline_search(inline_query):
    try:
        query = inline_query.query
        results = search_youtube(query)
        answers = []
        for i, result in enumerate(results):
            title = result['title']
            url = f"https://www.youtube.com/watch?v={result['id']}"
            answers.append(
                types.InlineQueryResultArticle(
                    id=str(i),
                    title=title,
                    description=f"Süre: {result['duration']} | Görüntüleme: {result['views']}",
                    input_message_content=types.InputTextMessageContent(message_text=f"{title}\n{url}"),
                    reply_markup=types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("İndir", callback_data=f"download_{url}"))
                )
            )
        bot.answer_inline_query(inline_query.id, answers, cache_time=1)
    except Exception as e:
        print(f"Satır içi hata: {e}")

@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    chat_id = call.message.chat.id
    message_id = call.message.message_id
    
    if call.data.startswith('download_'):
        url = call.data.split('download_')[1]
        bot.edit_message_text(chat_id=chat_id, message_id=message_id, text="İndirme işlemi başlatıldı, lütfen bekleyin...")
        Thread(target=download_audio, args=(url, chat_id, message_id)).start()
        bot.answer_callback_query(call.id, "İndirme başladı.")
    
    elif call.data.startswith('more_'):
        query, offset = call.data.split('_')[1], int(call.data.split('_')[2])
        new_results = YoutubeSearch(query, max_results=8).to_dict()[offset:offset+8]
        markup = types.InlineKeyboardMarkup()
        for i, result in enumerate(new_results, offset+1):
            title = result['title'][:40] + "..." if len(result['title']) > 40 else result['title']
            url = f"https://www.youtube.com/watch?v={result['id']}"
            markup.add(types.InlineKeyboardButton(f"{i}. {title}", callback_data=f"download_{url}"))
        if new_results:
            markup.add(types.InlineKeyboardButton("Daha Fazlası", callback_data=f"more_{query}_{offset+8}"))
        bot.edit_message_text(chat_id=chat_id, message_id=message_id, text=f"'{query}' için daha fazla sonuç:", reply_markup=markup)
        bot.answer_callback_query(call.id)

if not os.path.exists('downloads'):
    os.makedirs('downloads')

print("Bot başlatıldı.")
bot.polling(none_stop=True)
