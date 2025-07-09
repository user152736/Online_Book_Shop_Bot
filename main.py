import logging
import sys

from aiogram import Dispatcher, Bot
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.types import BotCommand
from aiogram.utils.i18n import I18n, FSMI18nMiddleware
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
from aiohttp import web

from bot.config import TOKEN
from bot.utils.starter import router
from db import database

dp = Dispatcher()
WEB_SERVER_HOST = "127.0.0.1"
WEB_SERVER_PORT = 8080  # Changed from 80 to 8080
WEBHOOK_PATH = "/webhook"
BASE_WEBHOOK_URL = "https://jasur.fil.uz"


async def on_startup(bot: Bot):
    logging.info("Starting up...")
    # Initialize database
    await database.create_all()

    # Set bot commands
    command_list = [
        BotCommand(command='start', description='Start the bot 🪡'),
        BotCommand(command='help', description='Help 🔓'),
        BotCommand(command='language', description='Change language 🔄')
    ]
    await bot.set_my_commands(command_list)

    # Check current webhook status
    try:
        current_webhook = await bot.get_webhook_info()
        expected_webhook_url = f"{BASE_WEBHOOK_URL}{WEBHOOK_PATH}"

        if current_webhook.url != expected_webhook_url:
            logging.info("Setting webhook...")
            await bot.set_webhook(expected_webhook_url)
        else:
            logging.info("Webhook already set.")
    except Exception as e:
        logging.error(f"Failed to set webhook: {e}")


async def on_shutdown(bot: Bot):
    await bot.delete_my_commands()


def main() -> None:
    i18n = I18n(path="locales")
    dp.update.outer_middleware.register(FSMI18nMiddleware(i18n))
    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)

    dp.include_router(router)
    dp.startup.register(on_startup)
    bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    app = web.Application()

    webhook_requests_handler = SimpleRequestHandler(
        dispatcher=dp,
        bot=bot,
    )
    webhook_requests_handler.register(app, path=WEBHOOK_PATH)

    setup_application(app, dp, bot=bot)

    web.run_app(app, host=WEB_SERVER_HOST, port=WEB_SERVER_PORT)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    main()
