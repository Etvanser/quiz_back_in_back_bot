import aiosqlite

from core.database_manager.base_database_handler import BaseDatabaseHandler, TableConfig
from logger import Logger


logger = Logger().get_logger()


class CreatorDatabase(BaseDatabaseHandler):
    """
    Инициализатор БД и таблиц

    """

    def __init__(self) -> None:
        """
        Создает экземпляр CreatorDatabase
        """
        super().__init__()

    async def __table_exists(self, table_name: str) -> bool:
        """
        Проверка существования таблицы

        :return: True если таблица существует, False если нет или произошла ошибка
        """
        try:
            result = await self._execute(
                "SELECT count(*) FROM sqlite_master WHERE type='table' AND name=?",
                (table_name,),
                fetch=True
            )
            exists = bool(result and result[0]['count(*)'] > 0)
            logger.debug(
                f"Проверка существования таблицы {table_name}: {'существует' if exists else 'не существует'}")
            return exists
        except aiosqlite.Error as e:
            logger.error(f"Ошибка проверки таблицы: {e}")
            return False

    async def __validate_existing_table(self, table_name: str, columns: dict[str, str]) -> bool:
        """
        Валидирует структуру существующей таблицы согласно конфигурации.

        :return: True если структура соответствует конфигурации, False в противном случае
        """
        if not await self.__table_exists(table_name):
            logger.warning(f"Таблица {table_name} не существует для валидации")
            return False

        try:
            result = await self._execute(
                f"PRAGMA table_info({table_name})",
                fetch=True
            )
            existing_columns = {row["name"]: row["type"] for row in result}

            # Проверка всех колонок из конфига
            for col, typ in columns.items():
                if col not in existing_columns:
                    logger.warning(f"Колонка {col} отсутствует в таблице {table_name}")
                    return False
                if existing_columns[col] != typ:
                    logger.warning(f"Тип колонки {col} не совпадает: ожидалось {typ}, получено {existing_columns[col]}")
            logger.debug(f"Таблица {table_name} прошла валидацию структуры")
            return True
        except aiosqlite.Error as e:
            logger.error(f"Ошибка валидации таблицы {table_name}: {e}")
            return False

    async def __create_table(self, table: TableConfig) -> bool:
        """
        Создание таблицы
        """
        try:
            columns_sql = ", ".join(
                f'"{col}" {typ}' for col, typ in table.columns.items()
            )
            await self._execute(
                f'CREATE TABLE "{table.table_name}" ({columns_sql})'
            )
            logger.info(f"Таблица {table.table_name} успешно создана")
            return True
        except Exception as e:
            logger.error(f"Ошибка создания таблицы {table.table_name}: {e}")
            return False

    async def init_db(self) -> bool:
        """
        Инициализация БД

        :return: Флаг успешной инициализации
        """
        logger.info(f"Инициализация БД {self._db_file}")

        try:
            for table in self._conf_data.tables:
                if await self.__table_exists(table.table_name):
                    if self._conf_data.safe_mode:
                        if not await self.__validate_existing_table(
                                table_name=table.table_name,
                                columns=table.columns
                        ):
                            logger.error(f"Несоответствие структуры таблицы {table.table_name} конфигу")
                            return False
                    # safe_mode отключен или структура соответствует
                    continue

                # Таблицы не существует - создаем
                if not await self.__create_table(table):
                    return False

            return True
        except Exception as e:
            logger.error(f"Ошибка инициализации БД: {e}")
            return False
