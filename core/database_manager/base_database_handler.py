"""
Модуль для асинхронной работы с базой данных пользователей через aiosqlite.

Содержит класс BaseDatabaseHandler, который предоставляет методы для:
- Инициализации БД
- Управления структурой таблиц

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
    table_name: str
    columns: dict[str,str]

@dataclass
class DatabaseConfig:
    id_bot: str
    db_file: str
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

        # tables_data = db_config_data.pop("tables")
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



    # async def user_exists(self, user_id: int) -> bool:
    #     """
    #     Проверяет существование пользователя в базе данных.
    #     :param user_id: Telegram ID пользователя для проверки
    #
    #     :return True если пользователь существует, False если нет или произошла ошибка
    #     """
    #     try:
    #         result = await self.__execute(
    #             f'SELECT 1 FROM "{self.__table_name}" WHERE user_id = ?',
    #             (user_id,),
    #             fetch=True
    #         )
    #         exists = bool(result)
    #         logger.debug(f"Пользователь {user_id} {'существует' if exists else 'не существует'} в БД")
    #         return exists
    #     except aiosqlite.Error as e:
    #         logger.error(f"Ошибка проверки пользователя {user_id}: {e}")
    #         return False
    #
    # async def add_user(
    #         self,
    #         user_id: int,
    #         username: Optional[str] = None,
    #         first_name: Optional[str] = None,
    #         last_name: Optional[str] = None,
    # ) -> bool:
    #     """
    #     Добавляет нового пользователя в базу данных.
    #     :param user_id: Telegram ID пользователя (обязательный)
    #     :param username: Telegram username (без @)
    #     :param first_name: Имя пользователя
    #     :param last_name: Фамилия пользователя
    #
    #     :return:
    #         bool: True если пользователь успешно добавлен, False если:
    #             - Пользователь уже существует
    #             - Таблица не существует
    #             - Произошла ошибка при добавлении
    #     Note:
    #         Перед добавлением проверяет существование таблицы и пользователя
    #     """
    #     logger.debug(f"Добавление пользователя ID: {user_id} в БД")
    #
    #     try:
    #         if not await self.__table_exists():
    #             logger.error(f"Таблица {self.__table_name} не существует")
    #             return False
    #
    #         if await self.user_exists(user_id):
    #             logger.debug(f"Пользователь {user_id} уже существует в БД")
    #             return False
    #
    #         await self.__execute(
    #             f"""
    #                     INSERT INTO "{self.__table_name}"
    #                     (user_id, username, first_name, last_name)
    #                     VALUES (?, ?, ?, ?)
    #                     """,
    #             (user_id, username, first_name, last_name)
    #         )
    #         logger.debug(f"Пользователь {user_id} успешно добавлен в БД")
    #         return True
    #     except aiosqlite.Error as e:
    #         logger.error(f"Ошибка при добавлении пользователя {user_id}: {e}")
    #         return False
    #
    # async def get_user(self, user_id: int) -> Optional[dict[str, Any]]:
    #     """
    #     Получает данные пользователя по его ID.
    #
    #     :param user_id: Telegram ID пользователя
    #
    #     :return: Словарь с данными пользователя если найден,
    #             None если пользователь не существует или произошла ошибка
    #     """
    #     logger.debug(f"Получение данных пользователя {user_id}")
    #     try:
    #         result = await self.__execute(
    #             f'SELECT * FROM "{self.__table_name}" WHERE user_id = ?',
    #             (user_id,),
    #             fetch=True
    #         )
    #         if result:
    #             logger.debug(f"Данные пользователя {user_id} успешно получены")
    #             return dict(result[0])
    #         logger.debug(f"Пользователь {user_id} не найден в БД")
    #         return None
    #     except aiosqlite.Error as e:
    #         logger.error(f"Ошибка получения данных пользователя {user_id}: {e}")
    #         return None
