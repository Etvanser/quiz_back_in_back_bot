"""
Модуль для асинхронной работы с базой данных пользователей через aiosqlite.

Содержит класс BaseDatabaseHandler, который предоставляет методы для:
- Инициализации БД

Для работы требуется установка aiosqlite: pip install aiosqlite
"""
from dataclasses import dataclass
from pathlib import Path

import aiosqlite
from typing import Optional, Any

from _singleton import Singleton
from const import BD_CONFIG, PathLike
from logger import Logger
from utils import load_config

logger = Logger().get_logger()


@dataclass
class TableConfig:
    """
    Конфигурация таблицы
    """
    # Имя таблицы
    table_name: str
    # Имя колонок таблицы
    columns: dict[str,str]

@dataclass
class DatabaseConfig:
    """
    Конфигурация БД
    """
    # ID Бота
    id_bot: str
    # Имя файла БД
    db_file: str
    # Таблицы в БД
    tables: list[TableConfig]
    safe_mode: bool = False


class ConfigDatabaseLoader(dict):
    """
    Загрузчик основных настроек БД
    """
    def __init__(self, config_file: str = None) -> None:
        super().__init__()
        self.config = load_config(config_file or BD_CONFIG)

        db_config_data = self.config.get("db_config", {})

        tables = []
        for table_data in db_config_data.pop("tables"):
            table_config = TableConfig(**table_data)
            tables.append(table_config)

        db_config = DatabaseConfig(
            **db_config_data,
            tables=tables
        )
        self["db_config"] = db_config

    def get_table_config(self, table_name: str) -> TableConfig | None:
        """
        Получить конфигурацию таблицы по имени

        :param table_name: Имя таблицы
        """
        db_config = self["db_config"]
        for table in db_config.tables:
            if table.table_name == table_name:
                return table
        return None


class BaseDatabaseHandler(metaclass=Singleton):
    """
    Обработчик базы данных
    """
    _conf_data: DatabaseConfig
    _db_file: PathLike

    def __init__(self) -> None:
        """
        Конструктор обработчика базы данных
        """
        self._conf_data: DatabaseConfig = ConfigDatabaseLoader().get("db_config")
        self._db_file = Path(self._conf_data.db_file)
        self._db_file.parent.mkdir(parents=True, exist_ok=True)

    async def _execute(
            self,
            query: str,
            params: tuple[Any, ...] = (),
            fetch: bool = False,
    ) -> Optional[list[dict[str, Any]]]:
        """
        Универсальный метод выполнения запроса

        :param query: SQL-запрос для выполнения
        :param params: Параметры для запроса
        :param fetch: Если True, возвращает результат запроса

        :return Результат запроса (только если fetch=True)
        """
        try:
            async with aiosqlite.connect(self._db_file) as conn:
                conn.row_factory = aiosqlite.Row
                async with conn.cursor() as cursor:
                    await cursor.execute(query, params)

                    if fetch:
                        result = await cursor.fetchall()
                        return [dict(row) for row in result] if result else None

                    await conn.commit()
                    return None

        except aiosqlite.Error as e:
            logger.error(f"Ошибка выполнения запроса: {e}\nQuery: {query}\nParams: {params}")
            return None
        except Exception as e:
            logger.error(f"Неожиданная ошибка при выполнении запроса: {e}")
            return None
