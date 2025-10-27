from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from core.database_manager.db_users_handler import DatabaseUserHandler, UserRole
from core.locale.locale import Locale
from core.routers.admin_panel import AdminStates, AdminMessageSender, AdminKeyboardBuilder
from errors import ErrorCode
from logger import Logger


class UsersManagerService:

    def __init__(self, user_handler: DatabaseUserHandler, keyboard: AdminKeyboardBuilder):
        self.locale = Locale()
        self.logger = Logger().get_logger()
        self.keyboard = keyboard
        self.user_handler = user_handler

    async def manage_users_panel(self, callback: CallbackQuery, state: FSMContext) -> None:
        """
        Панель управления пользователями - ВТОРОЙ УРОВЕНЬ

        :param callback: Callback запрос от кнопки
        :param state: Состояние FSM
        """
        self.logger.info(f"Админ {callback.from_user.id} открыл панель управления пользователями")
        await state.clear()

        try:
            await AdminMessageSender().send_or_edit_message(
                target=callback,
                text=self.locale.ui.get("admin_users_management_desc"),
                reply_markup=self.keyboard.admin_users_management_menu
            )
        except Exception as e:
            self.logger.error(f"Ошибка при отображении панели управления пользователями: {str(e)}")
            await callback.message.answer(self.locale.bot.get("error_display_admin_panel"))

        await callback.answer()

    async def add_user_callback(self, callback: CallbackQuery, state: FSMContext) -> None:
        """
        Обработка нажатия кнопки "Добавить пользователя" - ЕДИНСТВЕННЫЙ способ начать добавление

        :param callback: Callback запрос от кнопки
        :param state: Состояние FSM
        """
        self.logger.info(f"Админ {callback.from_user.id} нажал кнопку 'Добавить пользователя'")

        try:
            await state.clear()
            await AdminMessageSender().send_or_edit_message(
                target=callback,
                text=self.locale.ui.get("add_user_desc"),
                reply_markup=self.keyboard.create_single_button(
                    text=self.locale.buttons.get("btn_back"),
                    callback_data="back_to_admin"
                )
            )

            await state.set_state(AdminStates.waiting_for_user_input)
            await callback.answer()

        except Exception as e:
            self.logger.error(f"Ошибка при обработке callback добавления пользователя: {str(e)}", exc_info=True)
            await callback.answer(self.locale.bot.get("error_add_user_msg"))

    async def process_user_input(self, message: Message, state: FSMContext) -> None:
        """
        Обработка пересланного сообщение

        :param message: Сообщение от пользователя
        :param state: Состояние FSM
        """
        self.logger.debug(f"Обработка ввода от админа {message.from_user.id}: {message.text}")

        if not message.forward_from:
            await self.handle_invalid_input(message)
            return

        await self.handle_forwarded_message(message, state)

    async def handle_invalid_input(self, message: Message) -> None:
        """
        Обработка некорректного ввода (не пересланное сообщение)
        """
        admin_id = message.from_user.id
        self.logger.warning(f"Админ {admin_id} отправил непересланное сообщение: {message.text}")

        text = self.locale.bot.get("error_input_forward_msg")
        await AdminMessageSender().send_or_edit_message(
            target=message,
            text=text,
            reply_markup=self.keyboard.create_single_button(
                text=self.locale.buttons.get("btn_back"),
                callback_data="back_to_admin"
            )
        )

    async def handle_forwarded_message(self, message: Message, state: FSMContext) -> None:
        """
        Обработка пересланного сообщения

        :param message: Пересланное сообщение
        :param state: Состояние FSM
        """
        forwarded_from = message.forward_from
        self.logger.info(
            f"Админ {message.from_user.id} переслал сообщение от пользователя: {forwarded_from.id}")

        try:
            user_id = forwarded_from.id
            username = forwarded_from.username or ""
            first_name = forwarded_from.first_name or ""
            last_name = forwarded_from.last_name or ""

            if await self.user_handler.user_exists(user_id):
                self.logger.warning(
                    f"Попытка добавить существующего пользователя {user_id} через пересланное сообщение")

                text = self.locale.bot.get("warning_user_is_exists").format(
                    user_id=user_id,
                    username=username if username else "не указан",
                    first_name=first_name,
                    last_name=last_name,
                )
                await AdminMessageSender().send_or_edit_message(
                    target=message,
                    text=text,
                    reply_markup=self.keyboard.create_single_button(
                        text=self.locale.buttons.get("btn_back"),
                        callback_data="back_to_admin"
                    )
                )
                return

            await state.update_data(
                user_id=user_id,
                username=username,
                first_name=first_name,
                last_name=last_name
            )
            self.logger.debug(f"Данные пользователя {user_id} сохранены в состоянии")
            await self.ask_for_role(message, state, user_id, username, first_name, last_name)

        except Exception as e:
            self.logger.error(f"Ошибка при обработке пересланного сообщения: {str(e)}", exc_info=True)
            await message.answer("❌ Произошла ошибка при обработке пересланного сообщения.")

    async def ask_for_role(
            self,
            message: Message,
            state: FSMContext,
            user_id: int,
            username: str,
            first_name: str,
            last_name: str
    ) -> None:
        """
        Запрос роли у администратора

        :param message: Сообщение от администратора
        :param state: Состояние FSM
        :param user_id: ID пользователя
        :param username: Username пользователя
        :param first_name: Имя пользователя
        :param last_name: Фамилия пользователя
        """
        await state.update_data(username=username)

        text = self.locale.ui.get("add_user_data_desc").format(
            user_id=user_id,
            username=username if username else "не указан",
            first_name=first_name or "",
            last_name=last_name or "",
        )

        await AdminMessageSender().send_or_edit_message(
            target=message,
            text=text,
            reply_markup=self.keyboard.role_selection_keyboard
        )
        await state.set_state(AdminStates.waiting_for_role)
        self.logger.debug(f"Установлено состояние waiting_for_role для админа {message.from_user.id}")

    async def delete_users_callback(self, callback: CallbackQuery) -> None:
        """
        Обработка нажатия кнопки "Удалить пользователя"

         :param callback: Callback запрос от кнопки
        """
        self.logger.info(f"Админ {callback.from_user.id} нажал кнопку 'Удалить пользователя'")

        try:
            users = await self.user_handler.get_all_users()

            if not users:
                text = self.locale.ui.get("delete_users_users_not_found")
                await AdminMessageSender().send_or_edit_message(
                    target=callback,
                    text=text,
                    reply_markup=self.keyboard.create_single_button(
                        text=self.locale.buttons.get("btn_back"),
                        callback_data="back_to_admin"
                    )
                )
                return

            text = self.locale.ui.get("delete_users_desc")
            await AdminMessageSender().send_or_edit_message(
                target=callback,
                text=text,
                reply_markup=self.keyboard.create_delete_user_list_keyboard(users)
            )

        except Exception as e:
            self.logger.error(f"Ошибка при отображении списка для удаления: {str(e)}", exc_info=True)
            await callback.answer(self.locale.bot.get("error_users_list"))

    async def delete_user_callback(self, callback: CallbackQuery, state: FSMContext) -> None:
        """
        Обработка выбора пользователя для удаления

        :param callback: Callback запрос от кнопки
        :param state: Состояние FSM
        """
        try:
            user_id = int(callback.data.split("_")[2])
            self.logger.info(f"Админ {callback.from_user.id} выбрал для удаления пользователя {user_id}")

            user_exists = await self.user_handler.user_exists(user_id)
            if not user_exists:
                await callback.answer(self.locale.bot.get("error_user_not_found"))
                return

            user_role = await self.user_handler.get_user_role(user_id)

            if user_role == UserRole.ADMIN:
                await callback.answer(self.locale.bot.get("warning_delete_admin"))
                return

            await state.update_data(delete_user_id=user_id)

            text = self.locale.ui.get("confirm_delete_desc").format(
                user_id=user_id,
                user_role=user_role.value
            )
            await AdminMessageSender().send_or_edit_message(
                target=callback,
                text=text,
                reply_markup=self.keyboard.create_confirmation_delete_user_keyboard(user_id)
            )
            await state.set_state(AdminStates.waiting_for_delete_confirmation)

        except Exception as e:
            self.logger.error(f"Ошибка при выборе пользователя для удаления: {str(e)}", exc_info=True)
            await callback.answer(self.locale.bot.get("error_selected_user_delete"))

    async def confirm_delete_callback(self, callback: CallbackQuery, state: FSMContext) -> None:
        """
        Подтверждение удаления пользователя

        :param callback: Callback запрос от кнопки
        :param state: Состояние FSM
        """
        try:
            # Извлекаем ID пользователя из callback data
            user_id = int(callback.data.split("_")[2])
            self.logger.info(f"Админ {callback.from_user.id} подтвердил удаление пользователя {user_id}")

            user_exists = await self.user_handler.user_exists(user_id)
            if not user_exists:
                await AdminMessageSender().send_or_edit_message(
                    target=callback,
                    text=self.locale.bot.get("error_user_not_found"),
                    reply_markup=self.keyboard.create_single_button(
                        text=self.locale.buttons.get("btn_back"),
                        callback_data="back_to_admin"
                    )
                )
                await state.clear()
                return

            user_role = await self.user_handler.get_user_role(user_id)
            if user_role == UserRole.ADMIN:
                await AdminMessageSender().send_or_edit_message(
                    target=callback,
                    text=self.locale.bot.get("error_delete_admin"),
                    reply_markup=self.keyboard.create_single_button(
                        text=self.locale.buttons.get("btn_back"),
                        callback_data="back_to_admin"
                    )
                )
                await state.clear()
                return

            # Удаляем пользователя из БД
            result = await self.user_handler.delete_user(user_id)

            if result == ErrorCode.SUCCESSFUL:
                text = self.locale.ui.get("user_deleted_successful_desc").format(
                    user_id=user_id,
                    user_role=user_role.value
                )
                await AdminMessageSender().send_or_edit_message(
                    target=callback,
                    text=text,
                    reply_markup=self.keyboard.create_single_button(
                        text=self.locale.buttons.get("btn_back"),
                        callback_data="back_to_admin"
                    )
                )

                admin_username = f"@{callback.from_user.username}" if callback.from_user.username else callback.from_user.full_name
                self.logger.info(
                    f"Администратор {admin_username} ({callback.from_user.id}) "
                    f"удалил пользователя {user_id}"
                )
            else:
                await AdminMessageSender().send_or_edit_message(
                    target=callback,
                    text=self.locale.bot.get("error_delete_user_desc"),
                    reply_markup=self.keyboard.create_single_button(
                        text=self.locale.buttons.get("btn_back"),
                        callback_data="back_to_admin"
                    )
                )
            await state.clear()

        except Exception as e:
            self.logger.error(f"Ошибка при подтверждении удаления: {str(e)}", exc_info=True)
            await AdminMessageSender().send_or_edit_message(
                target=callback,
                text=self.locale.bot.get("error_delete_user_desc"),
                reply_markup=self.keyboard.create_single_button(
                    text=self.locale.buttons.get("btn_back"),
                    callback_data="back_to_admin"
                )
            )
            await state.clear()

    async def cancel_delete_callback(self, callback: CallbackQuery, state: FSMContext) -> None:
        """
        Отмена удаления пользователя

        :param callback: Callback запрос от кнопки
        :param state: Состояние FSM
        """
        self.logger.info(f"Админ {callback.from_user.id} отменил удаление пользователя")
        await state.clear()
        await self.delete_users_callback(callback)

    async def users_list_callback(self, callback: CallbackQuery) -> None:
        """
        Обработка нажатия кнопки "Список пользователей" - ЕДИНСТВЕННЫЙ способ посмотреть список

        :param callback: Callback запрос от кнопки
        """
        self.logger.info(f"Админ {callback.from_user.id} нажал кнопку 'Список пользователей'")

        try:
            users = await self.user_handler.get_all_users()
            self.logger.debug(f"Получено {len(users)} пользователей из БД")

            if not users:
                await AdminMessageSender().send_or_edit_message(
                    target=callback,
                    text=self.locale.ui.get("users_list_empty"),
                    reply_markup=self.keyboard.create_single_button(
                        text=self.locale.buttons.get("btn_back"),
                        callback_data="back_to_admin"
                    )
                )
                self.logger.info("Список пользователей пуст")
            else:
                user_list = []
                for i, user in enumerate(users, 1):
                    username = f"@{user.get('username')}" if user.get('username') else "нет"
                    last_name = user.get("last_name") or ""
                    first_name = f"{user.get('first_name')} {last_name}"
                    role_icon = "🛠️" if user.get("role") == UserRole.ADMIN else "👤"
                    role_text = "Админ" if user.get("role") == UserRole.ADMIN else "Пользователь"

                    user_list.append(
                        f"{i}. {role_icon} ID: `{user['user_id']}` | {username} | {first_name} | {role_text}"
                    )

                text = self.locale.ui.get("users_list_desc").format(
                    users=len(users),
                    users_text="\n".join(user_list)
                )
                await AdminMessageSender().send_or_edit_message(
                    target=callback,
                    text=text,
                    reply_markup=self.keyboard.create_single_button(
                        text=self.locale.buttons.get("btn_back"),
                        callback_data="back_to_admin"
                    )
                )
                self.logger.info(f"Список из {len(users)} пользователей отправлен админу {callback.from_user.id}")

            await callback.answer()

        except Exception as e:
            self.logger.error(f"Ошибка при обработке callback списка пользователей: {str(e)}", exc_info=True)
            await callback.answer(self.locale.bot.get("error_get_users_list"))

    async def process_role_callback(self, callback: CallbackQuery, state: FSMContext) -> None:
        """
        Обработка выбора роли через callback
        """
        self.logger.debug(f"Обработка callback выбора роли от админа {callback.from_user.id}: {callback.data}")

        try:
            role_str = callback.data.split("_")[1]
            role = UserRole.USER if role_str == "user" else UserRole.ADMIN
            self.logger.info(f"Админ {callback.from_user.id} выбрал роль: {role.value}")

            data = await state.get_data()
            user_id = data.get("user_id")
            username = data.get("username")
            first_name = data.get("first_name")
            last_name = data.get("last_name")

            self.logger.debug(f"Данные из состояния: user_id={user_id}, username={username}")

            if not user_id:
                self.logger.error("Не найден user_id в состоянии")
                await callback.message.edit_text("❌ Ошибка: данные сессии утеряны. Начните заново.")
                await state.clear()
                return

            self.logger.info(f"Попытка добавления пользователя {user_id} с ролью {role.value}")
            result = await self.user_handler.add_user(
                user_id=user_id,
                username=username,
                first_name=first_name,
                last_name=last_name,
                role=role
            )

            if result == ErrorCode.SUCCESSFUL:
                text = self.locale.ui.get("user_add_successful_desc").format(
                    user_id=user_id,
                    username = username if username else "не указан",
                    role="Пользователь" if role == UserRole.USER else "Админ"
                )

                await AdminMessageSender().send_or_edit_message(
                    target=callback,
                    text=text,
                    reply_markup=self.keyboard.create_single_button(
                        text=self.locale.buttons.get("btn_back"),
                        callback_data="back_to_admin"
                    )
                )

                admin_username = f"@{callback.from_user.username}" if callback.from_user.username else callback.from_user.full_name
                self.logger.info(
                    f"Администратор {admin_username} ({callback.from_user.id}) "
                    f"успешно добавил пользователя {user_id} с ролью {role.value}"
                )
            else:
                self.logger.error(f"Ошибка при добавлении пользователя {user_id}: {result}")
                await AdminMessageSender().send_or_edit_message(
                    target=callback,
                    text=self.locale.bot.get("error_add_user"),
                    reply_markup=self.keyboard.create_single_button(
                        text=self.locale.buttons.get("btn_back"),
                        callback_data="back_to_admin"
                    )
                )
            await state.clear()
            self.logger.debug(f"Состояние очищено для админа {callback.from_user.id}")
            await callback.answer()

        except Exception as e:
            self.logger.error(f"Ошибка при обработке выбора роли: {str(e)}", exc_info=True)
            await callback.message.edit_text(self.locale.bot.get("error_add_user"))
            await state.clear()
            await callback.answer()
