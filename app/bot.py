from aiogram import Bot, Dispatcher, F
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart
from aiogram.types import KeyboardButton, Message, ReplyKeyboardMarkup, WebAppInfo

from app.config import settings

bot = Bot(
    settings.bot_token,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML),
)
dp = Dispatcher()


def main_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Открыть кассу", web_app=WebAppInfo(url=settings.webapp_url))]
        ],
        resize_keyboard=True,
    )


@dp.message(CommandStart())
async def start(message: Message) -> None:
    if message.from_user.id not in settings.staff_id_set:
        await message.answer("Касса студии закрыта. Доступа нет.")
        return
    await message.answer(
        "Касса студии.\nТолько вы и партнёр видите цифры.\nНажмите кнопку ниже.",
        reply_markup=main_kb(),
    )


@dp.message(F.text)
async def fallback(message: Message) -> None:
    if message.from_user.id not in settings.staff_id_set:
        return
    await message.answer("Касса открывается кнопкой ниже.", reply_markup=main_kb())
