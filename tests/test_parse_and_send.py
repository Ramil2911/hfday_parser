import tempfile
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

from aiogram.exceptions import TelegramRetryAfter
from aiogram.methods import SendMessage

from parse_and_send import get_unsent_messages, send_to_channel


class ParseAndSendTests(unittest.IsolatedAsyncioTestCase):
    def make_bot(self, side_effect):
        bot = MagicMock()
        bot.send_message = AsyncMock(side_effect=side_effect)
        bot.session.close = AsyncMock()
        return bot

    def test_unsent_messages_are_unique(self):
        article = {
            "id": "new",
            "url": "https://example.com/article",
            "data": {
                "emoji": "🧪",
                "ru": {"title": "Title", "desc": "Description"},
                "categories": ["#ml"],
            },
        }
        data = {"papers": [{**article, "id": "sent"}, article, article]}

        messages = get_unsent_messages(data, {"sent"})

        self.assertEqual([article_id for article_id, _ in messages], ["new"])

    async def test_retry_after_is_respected_and_id_is_recorded_once(self):
        retry = TelegramRetryAfter(
            method=SendMessage(chat_id="@hf_daily_parser", text="message"),
            message="Too Many Requests",
            retry_after=38,
        )
        bot = self.make_bot([retry, object()])

        with tempfile.TemporaryDirectory() as directory:
            sent_ids_path = Path(directory) / "sent_articles.txt"
            sleep = AsyncMock()
            with patch("parse_and_send.Bot", return_value=bot), patch(
                "parse_and_send.asyncio.sleep", sleep
            ):
                await send_to_channel([("article-1", "message")], sent_ids_path)

            sleep.assert_awaited_once_with(38)
            self.assertEqual(bot.send_message.await_count, 2)
            self.assertEqual(sent_ids_path.read_text().splitlines(), ["article-1"])

    async def test_successful_ids_survive_a_later_send_failure(self):
        bot = self.make_bot([object(), RuntimeError("send failed")])

        with tempfile.TemporaryDirectory() as directory:
            sent_ids_path = Path(directory) / "sent_articles.txt"
            sleep = AsyncMock()
            with patch("parse_and_send.Bot", return_value=bot), patch(
                "parse_and_send.asyncio.sleep", sleep
            ):
                with self.assertRaisesRegex(RuntimeError, "send failed"):
                    await send_to_channel(
                        [("article-1", "first"), ("article-2", "second")],
                        sent_ids_path,
                    )

            self.assertEqual(sent_ids_path.read_text().splitlines(), ["article-1"])
            sleep.assert_awaited_once_with(1.5)
            bot.session.close.assert_awaited_once()


if __name__ == "__main__":
    unittest.main()
