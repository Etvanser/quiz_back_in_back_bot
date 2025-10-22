"""
Реализация логгера
"""
import logging
import os
from  logging import handlers
from datetime import datetime
from pathlib import Path
from typing import Optional


from const import PathLike, LOGGER_DIR
from _singleton import Singleton


class Logger(metaclass=Singleton):
    """
    Логгер проекта с записью только в файл
    """
    __log_file: Path
    __log_dir: Path
    __default_logger: logging.Logger
    __configured: bool

    def __init__(self, log_file: PathLike = "main_bot.log") -> None:
        """
        Конструктор logger

        :param log_file: Имя файла с логом
        """
        self.__configured = False
        self.timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        LOGGER_DIR.mkdir(parents=True, exist_ok=True)
        self.__log_dir = LOGGER_DIR / self.timestamp
        self.__log_dir.mkdir(exist_ok=True)
        self.__log_file = self.__log_dir / log_file
        self.__default_logger = logging.getLogger(str(self.__log_file.absolute()))

    def configure(
            self,
            level: int = logging.DEBUG,
    ) -> None:
        """
        Настройка логгера (вызывается один раз при старте проекта)

        :param level: Уровень логирования
        """
        if self.__configured:
            self.__default_logger.warning("Логгер уже был настроен ранее")
            return

        class CustomFormatter(logging.Formatter):
            """
            Кастомный форматер записи в лог
            """
            def format(self, record) -> str:
                """
                Форматирование записи

                :param record: Запись
                :return: Отформатированная запись
                """
                rel_path = os.path.relpath(record.pathname, os.getcwd())
                record.filename = f"{rel_path}:{record.lineno}"
                return super().format(record)

        formatter = CustomFormatter(
            fmt="%(asctime)s | %(filename)s -- %(levelname)s -- %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
        # Очищаем предыдущие обработчики
        for handler in self.__default_logger.handlers[:]:
            self.__default_logger.removeHandler(handler)

        try:
            file_handler = logging.handlers.RotatingFileHandler(
                filename=self.__log_file,
                encoding="utf-8",
            )
            file_handler.setFormatter(formatter)
        except Exception as e:
            raise RuntimeError(f"Не удалось настроить файловый обработчик логов: {e}")

        self.__default_logger.setLevel(level)
        self.__default_logger.addHandler(file_handler)
        self.__default_logger.propagate = False

        self.__configured = True
        self.__default_logger.info(f"Логгер успешно настроен, файл: {self.__log_file}")

    def get_logger(self, name: Optional[str] = None) -> logging.Logger:
        """
        Возвращает настроенный логгер для модуля

        :param name: Имя лога
        """
        if not self.__configured:
            self.configure()

        return self.__default_logger if name is None else logging.getLogger(name)
