from pathlib import Path
from typing import Union


# Корень проекта
ROOT_DIR = Path(__file__).parent.resolve()
# Каталог с конфигурационными файлами
CONFIG_DIR = ROOT_DIR / "configs"
# Конфигурация бота
CONFIG_BOT = CONFIG_DIR / "config_bot.json"
# Каталог логов
LOGGER_DIR = ROOT_DIR / "logs"


# Конфиг БД
BD_CONFIG = CONFIG_DIR / "config_struct_bd.json"
# Каталог БД
BD_DIR = ROOT_DIR / "database"
# Каталог с фото игроков
PHOTOS_DIR = ROOT_DIR / "photos"
# Конфиг уровней игроков
CONFIG_LEVEL_PLAYERS = CONFIG_DIR / "config_level_players.json"


# Конфиг модулей локализации
LOCALE_MODULE_CONFIG = CONFIG_DIR / "config_locale_module.json"
# Конфиги локализации
LOCALE_CONFIGS = CONFIG_DIR / "locale"
# Конфиг с текстовками для кнопок
LOCALE_BUTTONS = LOCALE_CONFIGS / "locale.buttons.json"


PathLike = Union[Path, str]
