import asyncio
import threading

import uvicorn

from app.bot import bot, dp
from app.config import settings
from app.db import init_db


def run_api() -> None:
    uvicorn.run("app.main:app", host=settings.host, port=settings.port, reload=False)


async def run_bot() -> None:
    if settings.bot_token.endswith("REPLACE_ME"):
        print("BOT_TOKEN не задан — бот не запущен. Mini App доступен локально.")
        return
    await dp.start_polling(bot)


def main() -> None:
    init_db()
    thread = threading.Thread(target=run_api, daemon=True)
    thread.start()
    print(f"Mini App: {settings.webapp_url or f'http://127.0.0.1:{settings.port}'}")
    asyncio.run(run_bot())
    thread.join()


if __name__ == "__main__":
    main()
