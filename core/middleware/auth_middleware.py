from typing import Callable, Any, Awaitable

from aiogram import BaseMiddleware
from aiogram.dispatcher.flags import get_flag
from aiogram.types import Message, User

from core.database_manager.db_users_handler import DatabaseUserHandler
from logger import Logger


class AuthMiddleware(BaseMiddleware):
    """
    Middleware для проверки аутентификации пользователей и контроля доступа.

    Проверяет наличие пользователя в базе данных и его роль,
    а также контролирует доступ к защищенным ресурсам на основе ролей.
    """

    def __init__(self) -> None:
        """
        Инициализирует middleware.

        Создает экземпляр DatabaseUserHandler для работы с пользователями в БД.
        """
        self.user_handler = DatabaseUserHandler()

    async def __call__(
            self,
            handler: Callable[[Message, dict[str, Any]], Awaitable[Any]],
            event: Message,
            data: dict[str, Any]
    ) -> Any:
        """
        Обрабатывает входящее событие.

        :param handler: Обработчик события, который будет вызван если проверки пройдены
        :param event: Входящее событие (сообщение)
        :param data: Словарь с дополнительными данными

        :return: Результат выполнения handler или None если доступ запрещен
        """
        user: User = data.get("event_from_user")

        if not user:
            return await handler(event, data)

        # Проверяем, есть ли пользователь в БД
        user_exists = await self.user_handler.user_exists(user.id)

        if not user_exists:
            Logger().get_logger().warning(f"Доступ запрещен для пользователя {user.id}")

            # Если пользователя нет в БД, отправляем сообщение и прекращаем обработку
            if isinstance(event, Message):
                await event.answer(
                    "❌ Доступ запрещен. Вы не зарегистрированы в системе.\n\n"
                    "Обратитесь к администратору для получения доступа."
                )
            return None

        # Добавляем информацию о пользователе в data
        user_role = await self.user_handler.get_user_role(user.id)
        data["user_role"] = user_role
        data["user_handler"] = self.user_handler

        # Проверяем требуется ли админ доступ
        handler_role = get_flag(data, "role")
        if handler_role and user_role != handler_role:
            Logger().get_logger().warning(
                f"Попытка доступа к защищенному ресурсу: пользователь {user.id} "
                f"(роль: {user_role.value}) пытался получить доступ к {handler_role.value}"
            )
            if isinstance(event, Message):
                await event.answer("❌ У вас недостаточно прав для выполнения этой команды.")
            return None

        return await handler(event, data)
