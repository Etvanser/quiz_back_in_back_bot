import re
from abc import ABC
from typing import Any

from _singleton import Singleton
from const import LOCALE_MODULE_CONFIG, LOCALE_CONFIGS
from logger import Logger
from utils import load_config


logger = Logger().get_logger()


class BaseLocaleModule(ABC):
    """
    Базовый класс для модуля локализации
    """

    def __init__(self, data: dict[str, Any]) -> None:
        logger.debug(f"Инициализация BaseLocaleModule с {len(data)} элементами")
        self._data = data
        self._processed_data = {}
        self._process_data()
        logger.debug(f"BaseLocaleModule инициализирован, обработано {len(self._processed_data)} значений")

    def _process_data(self) -> None:
        """
        Обрабатывает данные модуля
        """
        logger.debug("Начало обработки данных модуля")
        processed_count = 0
        expanded_count = 0

        for key, value in self._data.items():
            if isinstance(value, str):
                original_value = value
                self._processed_data[key] = self._expand_value(value, self._data.items())
                if self._processed_data[key] != original_value:
                    expanded_count += 1
                    logger.debug(
                        f"Значение для ключа '{key}' было раскрыто: '{original_value}' -> '{self._processed_data[key]}'")
                processed_count += 1
            else:
                self._processed_data[key] = value
                processed_count += 1

        logger.info(f"Обработка данных модуля завершена: {processed_count} значений, {expanded_count} раскрыто")

    def _expand_value(self, value: str, config: Any, visited: set = None) -> str:
        """
        Форматирование текстовки
        """
        if visited is None:
            visited = set()

        if not isinstance(value, str):
            return value

        pattern = r'\{.*\}'
        if not re.search(pattern, value):
            return value

        value_hash = hash(value)
        if value_hash in visited:
            logger.warning(f"Обнаружена циклическая ссылка при раскрытии значения: '{value}'")
            return value
        visited.add(value_hash)

        replaces = {k: v for k, v in config if k in value and isinstance(v, str)}
        if not replaces:
            logger.debug(f"Не найдены замены для значения: '{value}'")
            return value

        logger.debug(f"Найдены замены для '{value}': {list(replaces.keys())}")

        for k, v in replaces.items():
            if re.search(pattern, v):
                logger.debug(f"Рекурсивное раскрытие значения для ключа '{k}': '{v}'")
                replaces[k] = self._expand_value(v, config, visited)

        result = value.format_map(replaces)
        logger.debug(f"Значение раскрыто: '{value}' -> '{result}'")
        return result

    def get(self, key: str, default: str = "") -> str:
        """
        Получает текстовку по ключу
        """
        result = self._processed_data.get(key, default)
        if result == default:
            logger.warning(f"Ключ '{key}' не найден в модуле, возвращено значение по умолчанию: '{default}'")
        else:
            logger.debug(f"Получено значение для ключа '{key}': '{result}'")
        return result


class UIModule(BaseLocaleModule):
    """
    Модуль UI текстовок
    """

    def __init__(self, data: dict[str, Any]) -> None:
        logger.info(f"Инициализация UIModule с {len(data)} UI текстовками")
        super().__init__(data)
        logger.info("UIModule успешно инициализирован")


class BotMessagesModule(BaseLocaleModule):
    """
    Модуль сообщений бота
    """

    def __init__(self, data: dict[str, Any]) -> None:
        logger.info(f"Инициализация BotMessagesModule с {len(data)} сообщениями бота")
        super().__init__(data)
        logger.info("BotMessagesModule успешно инициализирован")


class ButtonsModule(BaseLocaleModule):
    """
    Модуль текстовок кнопок
    """

    def __init__(self, data: dict[str, Any]) -> None:
        logger.info(f"Инициализация ButtonsModule с {len(data)} текстовками кнопок")
        super().__init__(data)
        logger.info("ButtonsModule успешно инициализирован")


class Locale(metaclass=Singleton):
    """
    Локализация бота с модульной структурой
    """

    def __init__(self, language: str = "ru") -> None:
        """
        Конструктор локализации

        :param language: Язык локализации
        """
        logger.info(f"Инициализация локализации для языка: {language}")
        self.language = language
        self.modules = {}
        self._config = self._load_config()
        self._load_modules()
        logger.info(f"Локализация успешно инициализирована. Загружено модулей: {len(self.modules)}")

    def _load_config(self) -> dict[str, Any]:
        """
        Загружает конфигурацию модулей
        """
        logger.debug(f"Загрузка конфигурации модулей из: {LOCALE_MODULE_CONFIG}")
        try:
            config = load_config(LOCALE_MODULE_CONFIG)
            logger.info(f"Конфигурация модулей успешно загружена, найдено модулей: {len(config.get('modules', {}))}")
            return config
        except Exception as e:
            logger.error(f"Ошибка загрузки конфигурации модулей из {LOCALE_MODULE_CONFIG}: {e}")
            raise

    def _load_modules(self) -> None:
        """
        Загружает все модули локализации на основе конфига
        """
        modules_config = self._config.get("modules", {})
        logger.info(f"Начало загрузки {len(modules_config)} модулей локализации")

        loaded_count = 0
        for module_name, module_info in modules_config.items():
            file_path = LOCALE_CONFIGS / module_info.get("file")
            class_name = module_info.get("class_name")

            logger.debug(f"Обработка модуля '{module_name}': файл={file_path}, класс={class_name}")

            if not file_path.exists():
                logger.warning(f"Файл модуля '{module_name}' не найден: {file_path}")
                continue

            try:
                data = load_config(file_path)
                logger.debug(f"Данные модуля '{module_name}' загружены, элементов: {len(data)}")

                module_class = self._get_module_class(class_name)
                if not module_class:
                    logger.error(f"Класс модуля '{class_name}' не найден для модуля '{module_name}'")
                    continue

                self.modules[module_name] = module_class(data)
                loaded_count += 1
                logger.info(f"Модуль '{module_name}' успешно загружен")

            except Exception as e:
                logger.error(f"Ошибка загрузки модуля '{module_name}': {e}")

        logger.info(f"Загрузка модулей завершена. Успешно загружено: {loaded_count}/{len(modules_config)}")

    def _get_module_class(self, class_name: str) -> type:
        """
        Возвращает класс модуля по имени класса
        """
        modules_map = {
            'UIModule': UIModule,
            'BotMessagesModule': BotMessagesModule,
            'ButtonsModule': ButtonsModule
        }

        result = modules_map.get(class_name)
        if not result:
            logger.error(
                f"Класс модуля '{class_name}' не найден в mappings. Доступные классы: {list(modules_map.keys())}")
        else:
            logger.debug(f"Найден класс модуля: {class_name} -> {result}")

        return result

    def get(self, module: str, key: str, default: str = "") -> str:
        """
        Получает текстовку из конкретного модуля

        :param module: Имя модуля
        :param key: Ключ значения
        :param default: Значение по умолчанию
        """
        logger.debug(f"Запрос значения: модуль='{module}', ключ='{key}'")

        if module not in self.modules:
            logger.warning(f"Модуль '{module}' не найден. Доступные модули: {list(self.modules.keys())}")
            return default

        result = self.modules[module].get(key, default)
        if result == default:
            logger.warning(f"Ключ '{key}' не найден в модуле '{module}'")
        else:
            logger.debug(f"Значение найдено: модуль='{module}', ключ='{key}' -> '{result}'")

        return result

    @property
    def ui(self) -> BaseLocaleModule:
        module = self.modules.get('ui', BaseLocaleModule({}))
        if not self.modules.get('ui'):
            logger.warning("Модуль 'ui' не найден, возвращен пустой модуль")
        return module

    @property
    def bot(self) -> BaseLocaleModule:
        module = self.modules.get('bot_messages', BaseLocaleModule({}))
        if not self.modules.get('bot_messages'):
            logger.warning("Модуль 'bot_messages' не найден, возвращен пустой модуль")
        return module

    @property
    def buttons(self) -> BaseLocaleModule:
        module = self.modules.get('buttons', BaseLocaleModule({}))
        if not self.modules.get('buttons'):
            logger.warning("Модуль 'buttons' не найден, возвращен пустой модуль")
        return module
