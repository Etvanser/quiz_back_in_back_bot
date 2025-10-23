from dataclasses import dataclass

from const import CONFIG_BOT
from _singleton import Singleton
from utils import load_config


@dataclass
class ConfigBot:
    """
    Основные параметры бота
    """
    # Ключ бота
    token: str
    # ID администраторов
    admin_ids: list[int]


class ConfigBotLoader(dict):
    """
    Загрузчик основных настроек бота
    """
    def __init__(self, config_file: str = None) -> None:
        super().__init__()
        self.config = config_file or CONFIG_BOT

        for key, value in load_config(self.config).items():
            self[key] = ConfigBot(**value)


class Config(metaclass=Singleton):
    """
    Основные настройки бота
    """
    def __init__(self, config_file: str = None) -> None:
        """
        Создает экземпляр класса Config

        :param config_file: Файл конфига в json формате
        """
        self._config_loader = ConfigBotLoader(config_file)

    @property
    def data(self) -> ConfigBot:
        """
        Данные конфига
        """
        return self._config_loader.get("config")

