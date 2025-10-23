from typing import Optional

from core import Config
from core.database_manager.base_database_handler import BaseDatabaseHandler
from core.database_manager.const_bd import TableBD
from errors import ErrorCode
from logger import Logger


class DatabaseBotSettingsHandler(BaseDatabaseHandler):
    """
    Обработчик таблицы с настройками бота
    """
    _table_name : TableBD

    def __init__(self):
        super().__init__()
        self._table_name = TableBD.BOT_SETTINGS.value

    async def set_token(
            self,
            token_bot: str = None,
            description: Optional[str] = None
    ) -> ErrorCode:
        """
        Установка или обновление токена бота

        :param token_bot: Токен бота
        :param description: Описание бота (опционально)
        :return: True если операция успешна, False в противном случае
        """
        # HACK пока берем токен из json(НУЖНО ПЕРЕДЕЛАТЬ)
        Logger().get_logger().debug(f"Начало установки токена для бота {self._conf_data.id_bot}")

        try:
            # Получаем токен из конфига
            try:
                token = Config().data.token
                if not token:
                    Logger().get_logger().error("Токен бота не найден в конфигурации")
                    return ErrorCode.TOKEN_ERROR
                Logger().get_logger().debug("Токен успешно получен из конфигурации")
            except Exception as e:
                Logger().get_logger().error(f"Ошибка загрузки конфигурации: {str(e)}")
                return ErrorCode.FAILED_ERROR

            # Проверяем существование записи
            try:
                existing = await self._execute(
                    f'SELECT 1 FROM "{self._table_name}" WHERE bot_id = ?',
                    (self._conf_data.id_bot,),
                    fetch=True
                )
                operation = "обновление" if existing else "создание"
                Logger().get_logger().debug(f"Определена операция: {operation} токена")
            except Exception as e:
                Logger().get_logger().error(f"Ошибка проверки существования записи: {str(e)}")
                return ErrorCode.FAILED_ERROR

            # Формируем запрос
            if existing:
                query = f'UPDATE "{self._table_name}" SET token = ?, description = ? WHERE bot_id = ?'
                params = (token, description, self._conf_data.id_bot)
            else:
                query = f'INSERT INTO "{self._table_name}" (bot_id, token, description) VALUES (?, ?, ?)'
                params = (self._conf_data.id_bot, token, description)

            # Выполняем запрос
            try:
                result = await self._execute(query, params)
                if result is None:
                    Logger().get_logger().info(f"Успешное {operation} токена для бота {self._conf_data.id_bot}")
                    return ErrorCode.SUCCESSFUL
                else:
                    Logger().get_logger().error(f"Ошибка при {operation} токена: {result}")
                    return ErrorCode.FAILED_ERROR
            except Exception as e:
                Logger().get_logger().error(f"Ошибка выполнения запроса {operation}: {str(e)}")
                return ErrorCode.INIT_DB_ERROR

        except Exception as e:
            Logger().get_logger().error(f"Неожиданная ошибка в set_token: {str(e)}")
            return ErrorCode.INIT_DB_ERROR

    async def get_token(self) -> Optional[str]:
        """
        Получение токена бота по его ID

        :return: Токен бота или None если не найден
        """
        try:
            result = await self._execute(
                f'SELECT token FROM "{self._table_name}" WHERE bot_id = ?',
                (self._conf_data.id_bot,),
                fetch=True
            )

            if not result:
                Logger().get_logger().warning(f"Токен для бота {self._conf_data.id_bot} не найден")
                return None

            token = result[0]['token']
            Logger().get_logger().debug(f"Успешно получен токен для бота {self._conf_data.id_bot}")
            return token

        except Exception as e:
            Logger().get_logger().error(f"Ошибка при получении токена: {str(e)}")
            return None
