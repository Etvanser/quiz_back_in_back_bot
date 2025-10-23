from enum import Enum
from typing import Optional

from aiogram import Bot

from core.database_manager.base_database_handler import BaseDatabaseHandler
from core.database_manager.const_bd import TableBD
from errors import ErrorCode
from logger import Logger


class UserRole(Enum):
    ADMIN = "admin"
    USER = "user"


class DatabaseUserHandler(BaseDatabaseHandler):
    """
    Обработчик таблицы пользователей
    """

    def __init__(self):
        super().__init__()
        self._table_name = TableBD.USERS.value

    async def user_exists(self, user_id: int) -> bool:
        """
        Проверяет существование пользователя
        """
        try:
            result = await self._execute(
                f'SELECT 1 FROM "{self._table_name}" WHERE user_id = ?',
                (user_id,),
                fetch=True
            )
            return bool(result)
        except Exception as e:
            Logger().get_logger().error(f"Ошибка проверки пользователя: {str(e)}")
            return False

    async def get_user_role(self, user_id: int) -> Optional[UserRole]:
        """
        Получает роль пользователя
        """
        try:
            result = await self._execute(
                f'SELECT role FROM "{self._table_name}" WHERE user_id = ?',
                (user_id,),
                fetch=True
            )

            if not result:
                return None

            role_str = result[0]['role']
            return UserRole(role_str) if role_str else UserRole.USER

        except Exception as e:
            Logger().get_logger().error(f"Ошибка получения роли пользователя: {str(e)}")
            return None

    async def add_user(
            self,
            user_id: int,
            username: str = None,
            first_name: str = None,
            last_name: str = None,
            role: UserRole = UserRole.USER
    ) -> ErrorCode:
        """
        Добавляет нового пользователя
        """
        try:
            # Проверяем, существует ли пользователь
            if await self.user_exists(user_id):
                # Обновляем данные существующего пользователя
                return await self.update_user(user_id, username, first_name, last_name, role)

            query = f'''
                   INSERT INTO "{self._table_name}" 
                   (user_id, username, first_name, last_name, role) 
                   VALUES (?, ?, ?, ?, ?)
               '''

            params = (user_id, username, first_name, last_name, role.value)

            result = await self._execute(query, params)

            if result is None:
                Logger().get_logger().info(f"Пользователь {user_id} успешно добавлен с ролью {role.value}")
                return ErrorCode.SUCCESSFUL
            else:
                Logger().get_logger().error(f"Ошибка добавления пользователя: {result}")
                return ErrorCode.FAILED_ERROR

        except Exception as e:
            Logger().get_logger().error(f"Ошибка добавления пользователя: {str(e)}")
            return ErrorCode.INIT_DB_ERROR

    async def update_user(
            self,
            user_id: int,
            username: str = None,
            first_name: str = None,
            last_name: str = None,
            role: UserRole = None
    ) -> ErrorCode:
        """
        Обновляет данные пользователя
        """
        try:
            # Собираем поля для обновления
            update_fields = []
            params = []

            if username is not None:
                update_fields.append("username = ?")
                params.append(username)
            if first_name is not None:
                update_fields.append("first_name = ?")
                params.append(first_name)
            if last_name is not None:
                update_fields.append("last_name = ?")
                params.append(last_name)
            if role is not None:
                update_fields.append("role = ?")
                params.append(role.value)

            if not update_fields:
                return ErrorCode.SUCCESSFUL  # Нечего обновлять

            params.append(user_id)

            query = f'''
                UPDATE "{self._table_name}" 
                SET {', '.join(update_fields)}
                WHERE user_id = ?
            '''

            result = await self._execute(query, tuple(params))

            if result is None:
                Logger().get_logger().info(f"Данные пользователя {user_id} успешно обновлены")
                return ErrorCode.SUCCESSFUL
            else:
                Logger().get_logger().error(f"Ошибка обновления пользователя: {result}")
                return ErrorCode.FAILED_ERROR

        except Exception as e:
            Logger().get_logger().error(f"Ошибка обновления пользователя: {str(e)}")
            return ErrorCode.INIT_DB_ERROR

    async def update_user_role(self, user_id: int, role: UserRole) -> ErrorCode:
        """
        Обновляет роль пользователя
        """
        return await self.update_user(user_id, role=role)

    async def init_admin_users(self, admin_ids: list[int], bot: Optional[Bot] = None) -> ErrorCode:
        """
        Инициализирует администраторов в БД с получением данных пользователя

        :param admin_ids: Список ID администраторов
        :param bot: Экземпляр бота для получения данных пользователя (опционально)
        :return: Результат операции
        """
        try:
            Logger().get_logger().info(f"Начало инициализации администраторов: {admin_ids}")

            success_count = 0
            error_count = 0
            skipped_count = 0

            for admin_id in admin_ids:

                # Получаем данные пользователя если доступен бот
                username = None
                if bot:
                    try:
                        # Получаем информацию о пользователе через API Telegram
                        user_chat = await bot.get_chat(admin_id)

                        username = user_chat.username
                        first_name = user_chat.first_name
                        last_name = user_chat.last_name

                        Logger().get_logger().debug(
                            f"Получены данные пользователя {admin_id}: "
                            f"username={username}, first_name={first_name}, last_name={last_name}"
                        )

                    except Exception as e:
                        Logger().get_logger().warning(
                            f"Не удалось получить данные пользователя {admin_id} через бота: {str(e)}. "
                            f"Используем значения по умолчанию"
                        )
                        # Устанавливаем значения по умолчанию если не удалось получить данные
                        first_name = "Admin"
                        last_name = "User"
                else:
                    Logger().get_logger().warning(
                        f"Бот не доступен для получения данных пользователя {admin_id}. "
                        f"Используем значения по умолчанию"
                    )
                    first_name = "Admin"
                    last_name = "User"

                # Добавляем администратора с полученными данными
                result = await self.add_user(
                    user_id=admin_id,
                    username=username,
                    first_name=first_name,
                    last_name=last_name,
                    role=UserRole.ADMIN
                )

                if result == ErrorCode.SUCCESSFUL:
                    success_count += 1
                    Logger().get_logger().info(f"Администратор {admin_id} успешно инициализирован")
                else:
                    error_count += 1
                    Logger().get_logger().error(f"Ошибка инициализации администратора {admin_id}: {result}")

            Logger().get_logger().info(
                f"Инициализация администраторов завершена: "
                f"успешно - {success_count}, пропущено - {skipped_count}, ошибок - {error_count}"
            )

            if error_count == 0 and success_count > 0:
                return ErrorCode.SUCCESSFUL
            elif success_count > 0:
                return ErrorCode.PARTIAL_SUCCESS
            elif skipped_count > 0:
                Logger().get_logger().info("Все администраторы уже существуют в БД")
                return ErrorCode.SUCCESSFUL
            else:
                return ErrorCode.FAILED_ERROR

        except Exception as e:
            Logger().get_logger().error(f"Критическая ошибка при инициализации администраторов: {str(e)}")
            return ErrorCode.INIT_DB_ERROR

    async def get_all_users(self) -> list[dict]:
        """
        Получает список всех пользователей

        :return: Список словарей с данными пользователей
        """
        try:
            result = await self._execute(
                f'SELECT user_id, username, first_name, last_name, role FROM "{self._table_name}" ORDER BY user_id',
                fetch=True
            )

            if not result:
                return []

            users = []
            for row in result:
                users.append({
                    'user_id': row['user_id'],
                    'username': row['username'],
                    'first_name': row['first_name'],
                    'last_name': row['last_name'],
                    'role': UserRole(row['role']) if row['role'] else UserRole.USER
                })

            return users

        except Exception as e:
            Logger().get_logger().error(f"Ошибка получения списка пользователей: {str(e)}")
            return []

    async def delete_user(self, user_id: int) -> ErrorCode:
        """
        Удаляет пользователя из БД

        :param user_id: ID пользователя для удаления
        :return: Результат операции
        """
        try:
            # Проверяем, существует ли пользователь
            if not await self.user_exists(user_id):
                Logger().get_logger().warning(f"Попытка удалить несуществующего пользователя {user_id}")
                return ErrorCode.FAILED_ERROR

            # Удаляем пользователя
            result = await self._execute(
                f'DELETE FROM "{self._table_name}" WHERE user_id = ?',
                (user_id,)
            )

            if result is None:
                Logger().get_logger().info(f"Пользователь {user_id} успешно удален")
                return ErrorCode.SUCCESSFUL
            else:
                Logger().get_logger().error(f"Ошибка удаления пользователя {user_id}: {result}")
                return ErrorCode.FAILED_ERROR

        except Exception as e:
            Logger().get_logger().error(f"Ошибка при удалении пользователя {user_id}: {str(e)}")
            return ErrorCode.INIT_DB_ERROR
