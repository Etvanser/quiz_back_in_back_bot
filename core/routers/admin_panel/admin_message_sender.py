from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup

from core.locale.locale import Locale


class AdminMessageSender:
    """
    Управление отправкой сообщений админ-панели
    """

    def __init__(self) -> None:
        self.locale = Locale()

    @staticmethod
    async def send_or_edit_message(
            target: Message | CallbackQuery,
            text: str,
            reply_markup: InlineKeyboardMarkup = None,
            parse_mode: str = "Markdown"
    ) -> None:
        """
        Универсальная отправка/редактирование сообщения
        """
        if isinstance(target, Message):
            await target.answer(text, reply_markup=reply_markup, parse_mode=parse_mode)
        else:
            await target.message.edit_text(text, reply_markup=reply_markup, parse_mode=parse_mode)
