from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

from core import Config
from core.database_manager.db_bot_settings_handler import DatabaseBotSettingsHandler
from core.database_manager.db_users_handler import DatabaseUserHandler
from core.middleware.auth_middleware import AuthMiddleware
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
        self._setup_middleware()
        self._dp.include_router(RoutersRecorder.setup_main_router())

    def _setup_middleware(self) -> None:
        """
        Настройка middleware для бота
        """
        auth_middleware = AuthMiddleware()
        # Регистрируем middleware для всех типов сообщений
        self._dp.message.middleware(auth_middleware)
        self._dp.callback_query.middleware(auth_middleware)
        # Можно добавить и для других типов событий при необходимости
        # self._dp.edited_message.middleware(auth_middleware)
        # self._dp.channel_post.middleware(auth_middleware)

    async def _init_admins(self) -> ErrorCode:
        """
        Инициализация администраторов в БД

        :return: Результат операции
        """
        try:
            Logger().get_logger().info("Начало инициализации администраторов")

            admin_ids = Config().data.admin_ids

            if not admin_ids:
                Logger().get_logger().warning("Список администраторов пуст в конфигурации")
                return ErrorCode.SUCCESSFUL

            user_handler = DatabaseUserHandler()
            result = await user_handler.init_admin_users(admin_ids, self._bot)

            if result == ErrorCode.SUCCESSFUL:
                Logger().get_logger().info("Администраторы успешно инициализированы")
            elif result == ErrorCode.PARTIAL_SUCCESS:
                Logger().get_logger().warning("Некоторые администраторы не были инициализированы")
            else:
                Logger().get_logger().error("Ошибка инициализации администраторов")

            return result

        except Exception as e:
            Logger().get_logger().error(f"Критическая ошибка при инициализации администраторов: {str(e)}")
            return ErrorCode.INIT_DB_ERROR

    async def init(self) -> ErrorCode:
        """
        Инициализация бота
        """
        Logger().get_logger().info("Начало инициализации бота")

        try:
            db_config_bot = DatabaseBotSettingsHandler()
            Logger().get_logger().debug("Создан экземпляр DatabaseBotSettingsHandler")
            Logger().get_logger().debug("Попытка получения токена из базы данных")
            token_bot = await db_config_bot.get_token()

            if token_bot is None:
                Logger().get_logger().warning("Токен не найден в базе данных. Попытка установки нового токена")

                set_result = await db_config_bot.set_token()
                if set_result != ErrorCode.SUCCESSFUL:
                    Logger().get_logger().error(f"Ошибка установки токена в базу данных: {set_result}")
                    return ErrorCode.TOKEN_ERROR

                Logger().get_logger().info("Токен успешно установлен в базу данных")
                Logger().get_logger().debug("Повторная попытка получения токена из базы данных")
                token_bot = await db_config_bot.get_token()

            if token_bot:
                Logger().get_logger().info("Токен успешно получен. Создание экземпляра Bot")
                self._bot = Bot(token=token_bot)
                admin_init_result = await self._init_admins()
                if admin_init_result == ErrorCode.FAILED_ERROR:
                    Logger().get_logger().error("Критическая ошибка инициализации администраторов")
                    return ErrorCode.FAILED_ERROR

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
