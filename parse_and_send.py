import json
import asyncio
from aiogram import Bot
import os

# Чтение уже отправленных ID
def read_sent_ids(file_path):
    if not os.path.exists(file_path):
        return set()  # Возвращаем пустое множество, если файл не существует
    with open(file_path, "r") as file:
        return set(line.strip() for line in file.readlines())

# Запись новых ID в файл
def write_sent_ids(file_path, sent_ids):
    with open(file_path, "a") as file:
        for article_id in sent_ids:
            file.write(article_id + "\n")

def load_data():
    # Открытие файла и чтение содержимого
    file_path = "hfday/hf_papers.json"

    text = None
    with open(file_path, "r", encoding="utf-8") as file:
        text = file.read()

    return json.loads(text)

async def send_to_channel(messages):
    # Создание экземпляра бота
    bot = Bot(token=os.getenv("TELEGRAM_BOT_TOKEN"))
    
    try:
        for message in messages:
            await bot.send_message(chat_id="@hf_daily_parser", text=message, parse_mode='HTML')
    finally:
        # Закрытие соединения с ботом
        await bot.session.close()
    

# Основной скрипт
if __name__ == "__main__":

    # Парсинг данных
    data = load_data()

    old_article_ids = read_sent_ids("sent_articles.txt")
    article_ids_to_send = set(article['id'] for article in data['papers'] if article['id'] not in old_article_ids)

    messages = [f"{article['data']['emoji']} <a href=\"{article['url']}\">{article['data']['ru']['title']}</a> \n\n{article['data']['ru']['desc']}\n\n{" ".join(article['data']["categories"])}\n\n" for article in data['papers'] if article['id'] in article_ids_to_send]
    asyncio.run(send_to_channel(messages))

    write_sent_ids("sent_articles.txt", old_article_ids | article_ids_to_send)