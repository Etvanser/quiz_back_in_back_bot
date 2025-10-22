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


PathLike = Union[Path, str]
