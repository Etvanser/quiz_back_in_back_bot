from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

from core.database_manager.db_bot_settings_handler import DatabaseBotSettingsHandler
from core.router_recorder.router_recorder import RoutersRecorder
from errors import ErrorCode
from logger import Logger


class EngineBot:
    """
    Движок бота
    """
    _bot: Bot

    def __init__(self) -> None:
        """
        Создает экземпляр EngineBot
        """
        self._dp = Dispatcher(storage=MemoryStorage())
        self._dp.include_router(RoutersRecorder.setup_main_router())

    async def init(self) -> ErrorCode:
        """
        Инициализация бота
        """
        Logger().get_logger().info("Начало инициализации бота")

        try:
            db_config_bot = DatabaseBotSettingsHandler()
            Logger().get_logger().debug("Создан экземпляр DatabaseBotSettingsHandler")

            # Получаем токен из базы данных
            Logger().get_logger().debug("Попытка получения токена из базы данных")
            token_bot = await db_config_bot.get_token()

            if token_bot is None:
                Logger().get_logger().warning("Токен не найден в базе данных. Попытка установки нового токена")

                # Устанавливаем токен
                set_result = await db_config_bot.set_token()
                if set_result != ErrorCode.SUCCESSFUL:
                    Logger().get_logger().error(f"Ошибка установки токена в базу данных: {set_result}")
                    return ErrorCode.TOKEN_ERROR

                Logger().get_logger().info("Токен успешно установлен в базу данных")

                # Повторно получаем токен
                Logger().get_logger().debug("Повторная попытка получения токена из базы данных")
                token_bot = await db_config_bot.get_token()

            if token_bot:
                Logger().get_logger().info("Токен успешно получен. Создание экземпляра Bot")
                self._bot = Bot(token=token_bot)
                Logger().get_logger().info("Бот успешно инициализирован")
                return ErrorCode.SUCCESSFUL
            else:
                Logger().get_logger().error("Не удалось получить токен после установки")
                return ErrorCode.TOKEN_ERROR

        except Exception as e:
            Logger().get_logger().error(f"Критическая ошибка при инициализации бота: {str(e)}", exc_info=True)
            return ErrorCode.INIT_DB_ERROR

    async def start(self) -> None:
        """
        Запуск бота
        """
        Logger().get_logger().info("Запуск бота: начало процедуры start_polling")

        try:
            await self._dp.start_polling(self._bot)
            Logger().get_logger().info("Бот успешно запущен и начал обработку сообщений")
        except Exception as e:
            Logger().get_logger().critical(f"Критическая ошибка при запуске бота: {str(e)}", exc_info=True)
            raise
        finally:
            Logger().get_logger().info("Завершение работы бота")
