from enum import Enum


class TableBD(str, Enum):
    """
    Название таблиц в БД
    """
    BOT_SETTINGS = "bot_settings"
    USERS = "users"
