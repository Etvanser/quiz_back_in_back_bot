from typing import Optional

from core.database_manager.creator_database import CreatorDatabase
from core.engine import EngineBot
from errors import ErrorCode
from logger import Logger


class Application:
    """
    Приложение бота
    """
    _engine: Optional[EngineBot]

    def __init__(self) -> None:
        """
        Конструктор приложения
        """

        self._engine = EngineBot()

    async def _init(self) -> ErrorCode:
        if await self._init_db() != ErrorCode.SUCCESSFUL:
            Logger().get_logger().error("Ошибка инициализации БД")
            return ErrorCode.FAILED_ERROR

        if await self._engine.init() != ErrorCode.SUCCESSFUL:
            Logger().get_logger().error("Ошибка инициализации Движка")
            return ErrorCode.FAILED_ERROR

        return ErrorCode.SUCCESSFUL

    async def _init_db(self) -> ErrorCode:
        """
        Инициализация БД и таблиц
        """
        creator_db = CreatorDatabase()
        if await creator_db.init_db():
            return ErrorCode.SUCCESSFUL
        else:
            return ErrorCode.INIT_DB_ERROR

    async def run(self) -> ErrorCode:
        """
        Запуск бота
        """
        Logger().get_logger().info("Запуск бота...")
        if await self._init() != ErrorCode.SUCCESSFUL:
            Logger().get_logger().info("Ошибка запуска бота...")
            return ErrorCode.FAILED_ERROR

        await self._engine.start()
        Logger().get_logger().info("Бот запущен")
        return ErrorCode.SUCCESSFUL
