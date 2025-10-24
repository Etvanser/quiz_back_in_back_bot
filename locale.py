import json
import re
from abc import ABC, abstractmethod

from _singleton import Singleton
from const import CONFIG_DIR


class BaseLocale(ABC):
    """
    Базовый класс локализации
    """
    def __init__(self, **kwargs) -> None:
        """
        Конструктор базового класса локализации
        """
        self._kwargs = kwargs
        self._init()
        self._forming_locale()

    @abstractmethod
    def _init(self) -> None:
        """
        Инициализирует локализацию
        """
        raise NotImplementedError

    @abstractmethod
    def _forming_locale(self) -> None:
        """
        Формирует локализацию
        """
        raise NotImplementedError

    @abstractmethod
    def get(self, key: str, default: str = "") -> str:
        """
        Берет элемент локализации

        :param key: Ключ значения
        :param default: Аргумент по умолчанию
        """
        raise NotImplementedError

    def _expand_value(self, value, config) -> dict:
        """
        Форматирование текстовки
        """
        if isinstance(value, dict):
            for k, v in value.items():
                value[k] = self._expand_value(v, config)
            return value
        pattern = '\{.*\}'
        if not re.search(pattern, value):
            return value
        replaces = {k: v for k, v in config if k in value and value not in v}
        if not replaces or len(replaces) < 1:
            return value
        #TODO Logger
        for k, v in replaces.items():
            if re.search(pattern, v):
                replaces[k] = self._expand_value(v, config)
        result = value.format_map(replaces)
        #TODO Logger
        return result


class UILocale(BaseLocale):
    """
    Локализация текстовок и элементов управления
    """
    # Список локализации элементов управления

    _extended: dict[str, str] = None

    def _init(self) -> None:
        """
        Инициализирует локализацию
        """
        self._extended = {}
        self._forming_locale()

    def _forming_locale(self) -> None:
        """
        Формируем локализацию
        """
        values = {k: v for k, v in self._kwargs.items()}
        format_value = ["first_name"]
        for k, v in values.items():
            #TODO Logger
            skip_expand = False
            for ignore in format_value:
                if ignore in v:
                    skip_expand = True
            if not skip_expand:
                v = self._expand_value(v, self._kwargs.items())
            self._extended[k] = v

    def get(self, key: str, default: str = "") -> str:
        """
        Берет элемент локализации

        :param key: Ключ значения
        :param default: Аргумент по умолчанию
        """
        return self._extended.get(key, default)


class Locale(metaclass=Singleton):
    """
    Локализация бота
    """
    ui: UILocale

    def __init__(self) -> None:
        """
        Конструктор локализации
        """
        config_file = f"locale.ru.json"
        self.ui = UILocale(**json.load(
            open(CONFIG_DIR / config_file)
        ))
