import json
import asyncio
from aiogram import Bot
from aiogram.exceptions import TelegramRetryAfter
import os

SEND_INTERVAL_SECONDS = 1.5

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

def get_unsent_messages(data, sent_ids):
    messages = []
    seen_ids = set(sent_ids)

    for article in data["papers"]:
        article_id = article["id"]
        if article_id in seen_ids:
            continue

        seen_ids.add(article_id)
        message = f"{article['data']['emoji']} <a href=\"{article['url']}\">{article['data']['ru']['title']}</a> \n\n{article['data']['ru']['desc']}\n\n{" ".join(article['data']["categories"])}\n\n"
        messages.append((article_id, message))

    return messages

def load_data():
    # Открытие файла и чтение содержимого
    file_path = "hfday/hf_papers.json"

    text = None
    with open(file_path, "r", encoding="utf-8") as file:
        text = file.read()

    return json.loads(text)

async def send_to_channel(messages, sent_ids_path="sent_articles.txt"):
    # Создание экземпляра бота
    bot = Bot(token=os.getenv("TELEGRAM_BOT_TOKEN"))

    try:
        for index, (article_id, message) in enumerate(messages):
            if index:
                await asyncio.sleep(SEND_INTERVAL_SECONDS)

            while True:
                try:
                    await bot.send_message(chat_id="@hf_daily_parser", text=message, parse_mode='HTML')
                    break
                except TelegramRetryAfter as error:
                    await asyncio.sleep(error.retry_after)

            # Persist each successful send so a later failure cannot resend it.
            write_sent_ids(sent_ids_path, [article_id])
    finally:
        # Закрытие соединения с ботом
        await bot.session.close()
    

# Основной скрипт
if __name__ == "__main__":

    # Парсинг данных
    data = load_data()

    old_article_ids = read_sent_ids("sent_articles.txt")
    messages = get_unsent_messages(data, old_article_ids)
    asyncio.run(send_to_channel(messages))
