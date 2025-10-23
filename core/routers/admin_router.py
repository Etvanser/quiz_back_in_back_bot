from aiogram import Router, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import Message, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder

from core.database_manager.db_user_handler import DatabaseUserHandler, UserRole
from core.router_recorder import RoutersRecorder
from core.routers import BaseRouter
from errors import ErrorCode
from logger import Logger


class AdminStates(StatesGroup):
    """
    Состояния для админских операций
    """
    waiting_for_user_input = State()
    waiting_for_username = State()
    waiting_for_role = State()
    waiting_for_delete_confirmation = State()


@RoutersRecorder.record_router
class AdminRouter(BaseRouter):
    """
    Роутер для административных команд
    """

    def __init__(self, router: Router) -> None:
        self.user_handler = DatabaseUserHandler()
        self.logger = Logger().get_logger()
        super().__init__(router)
        self.logger.info("AdminRouter инициализирован")

    async def _is_admin(self, user_id: int) -> bool:
        """
        Проверяет, является ли пользователь администратором по данным из БД
        """
        try:
            user_role = await self.user_handler.get_user_role(user_id)
            is_admin = user_role == UserRole.ADMIN if user_role else False

            self.logger.debug(f"Проверка прав доступа для {user_id}: роль={user_role}, is_admin={is_admin}")
            return is_admin

        except Exception as e:
            self.logger.error(f"Ошибка при проверке прав доступа для {user_id}: {str(e)}")
            return False

    def _register_handlers(self) -> None:
        """
        Регистрация обработчиков для администратора
        """
        self.logger.debug("Начало регистрации обработчиков AdminRouter")

        # Команды администратора - оставляем только /admin
        self.router.message(Command("admin"))(self.admin_panel)

        # Обработчики состояний для добавления пользователя
        self.router.message(AdminStates.waiting_for_user_input)(self.process_user_input)
        self.router.message(AdminStates.waiting_for_username)(self.process_username)
        self.router.message(AdminStates.waiting_for_role)(self.process_role)
        self.router.message(AdminStates.waiting_for_delete_confirmation)(self.process_delete_confirmation)

        # Callback-обработчики для кнопок
        self.router.callback_query(F.data == "add_user_cmd")(self.add_user_callback)
        self.router.callback_query(F.data == "users_list_cmd")(self.users_list_callback)
        self.router.callback_query(F.data == "delete_users_cmd")(self.delete_users_callback)
        self.router.callback_query(F.data.startswith("role_"))(self.process_role_callback)
        self.router.callback_query(F.data.startswith("quick_add_"))(self.process_quick_add_callback)
        self.router.callback_query(F.data.startswith("delete_user_"))(self.delete_user_callback)
        self.router.callback_query(F.data.startswith("confirm_delete_"))(self.confirm_delete_callback)
        self.router.callback_query(F.data.startswith("cancel_delete_"))(self.cancel_delete_callback)
        self.router.callback_query(F.data == "cancel_operation")(self.cancel_operation)
        self.router.callback_query(F.data == "back_to_admin")(self.back_to_admin_panel)
        self.router.callback_query(F.data == "back_to_user_input")(self.back_to_user_input)
        self.router.callback_query(F.data == "back_to_username")(self.back_to_username_input)

        self.logger.info("Обработчики AdminRouter успешно зарегистрированы")

    async def admin_panel(self, target: Message | CallbackQuery) -> None:
        """
        Панель администратора - ЕДИНСТВЕННАЯ точка входа, проверяющая права
        """
        if isinstance(target, Message):
            message = target
            user_id = message.from_user.id
        else:
            message = target.message
            user_id = target.from_user.id

        if not await self._is_admin(user_id):
            await message.answer("❌ Доступ запрещен. У вас нет прав администратора.")
            self.logger.warning(f"Попытка доступа к админ-панели от не-админа: {user_id}")
            return

        self.logger.info(f"Админ {user_id} вызвал панель администратора")

        try:
            keyboard = InlineKeyboardBuilder()
            keyboard.button(text="👥 Добавить пользователя", callback_data="add_user_cmd")
            keyboard.button(text="📋 Список пользователей", callback_data="users_list_cmd")
            keyboard.button(text="🗑️ Удалить пользователя", callback_data="delete_users_cmd")
            keyboard.button(text="❌ Закрыть", callback_data="cancel_operation")
            keyboard.adjust(1)

            if isinstance(target, Message):
                await message.answer(
                    "🛠️ **Панель администратора**\n\n"
                    "Выберите действие:",
                    reply_markup=keyboard.as_markup(),
                    parse_mode="Markdown"
                )
            else:
                await message.edit_text(
                    "🛠️ **Панель администратора**\n\n"
                    "Выберите действие:",
                    reply_markup=keyboard.as_markup(),
                    parse_mode="Markdown"
                )

            self.logger.debug(f"Панель администратора отправлена пользователю {user_id}")

        except Exception as e:
            self.logger.error(f"Ошибка при отображении панели администратора: {str(e)}", exc_info=True)
            await message.answer("❌ Произошла ошибка при отображении панели администратора.")

    async def back_to_admin_panel(self, callback: CallbackQuery, state: FSMContext) -> None:
        """
        Возврат в админ-панель
        """
        self.logger.info(f"Админ {callback.from_user.id} нажал 'Назад в админ-панель'")
        await state.clear()
        await self.admin_panel(callback)
        await callback.answer()

    async def add_user_callback(self, callback: CallbackQuery, state: FSMContext) -> None:
        """
        Обработка нажатия кнопки "Добавить пользователя" - ЕДИНСТВЕННЫЙ способ начать добавление
        """
        self.logger.info(f"Админ {callback.from_user.id} нажал кнопку 'Добавить пользователя'")

        try:
            await state.clear()

            # Создаем клавиатуру с кнопкой "Назад"
            keyboard = InlineKeyboardBuilder()
            keyboard.button(text="⬅️ Назад", callback_data="back_to_admin")
            keyboard.adjust(1)

            await callback.message.edit_text(
                "👤 **Добавление нового пользователя**\n\n"
                "Вы можете:\n"
                "• Ввести ID пользователя (только цифры)\n"
                "• Переслать сообщение от пользователя\n\n"
                "Отправьте ID или перешлите сообщение:",
                reply_markup=keyboard.as_markup()
            )
            await state.set_state(AdminStates.waiting_for_user_input)
            self.logger.debug(f"Установлено состояние waiting_for_user_input для админа {callback.from_user.id}")
            await callback.answer()

        except Exception as e:
            self.logger.error(f"Ошибка при обработке callback добавления пользователя: {str(e)}", exc_info=True)
            await callback.answer("❌ Ошибка при начале добавления пользователя.")

    async def process_user_input(self, message: Message, state: FSMContext) -> None:
        """
        Обработка ввода пользователя - ID или пересланное сообщение
        """
        self.logger.debug(f"Обработка ввода от админа {message.from_user.id}: {message.text}")

        try:
            # Проверяем, является ли сообщение пересланным
            if message.forward_from:
                await self._handle_forwarded_message(message, state)
                return

            # Если не пересланное сообщение, обрабатываем как ID
            user_id = int(message.text.strip())
            self.logger.info(f"Админ {message.from_user.id} ввел ID пользователя: {user_id}")

            # Проверяем, существует ли уже пользователь
            if await self.user_handler.user_exists(user_id):
                self.logger.warning(f"Попытка добавить существующего пользователя {user_id}")

                # Создаем клавиатуру с кнопкой "Назад"
                keyboard = InlineKeyboardBuilder()
                keyboard.button(text="⬅️ Назад", callback_data="back_to_admin")
                keyboard.adjust(1)

                await message.answer(
                    "❌ Пользователь с таким ID уже существует в системе.\n\n"
                    "Введите другой ID или перешлите сообщение от другого пользователя:",
                    reply_markup=keyboard.as_markup()
                )
                return

            # Сохраняем ID в состоянии
            await state.update_data(user_id=user_id)
            self.logger.debug(f"ID пользователя {user_id} сохранен в состоянии")

            # Переходим к вводу username
            await self._ask_for_username(message, state)

        except ValueError:
            self.logger.warning(f"Неверный формат ввода от админа {message.from_user.id}: {message.text}")

            # Создаем клавиатуру с кнопкой "Назад"
            keyboard = InlineKeyboardBuilder()
            keyboard.button(text="⬅️ Назад", callback_data="back_to_admin")
            keyboard.adjust(1)

            await message.answer(
                "❌ Неверный формат. Введите только цифры (ID) или перешлите сообщение от пользователя:\n"
                "Пример ID: 123456789",
                reply_markup=keyboard.as_markup()
            )
        except Exception as e:
            self.logger.error(f"Ошибка при обработке ввода пользователя: {str(e)}", exc_info=True)

            # Создаем клавиатуру с кнопкой "Назад"
            keyboard = InlineKeyboardBuilder()
            keyboard.button(text="⬅️ Назад", callback_data="back_to_admin")
            keyboard.adjust(1)

            await message.answer(
                "❌ Произошла ошибка при обработке ввода.",
                reply_markup=keyboard.as_markup()
            )

    async def _handle_forwarded_message(self, message: Message, state: FSMContext) -> None:
        """
        Обработка пересланного сообщения
        """
        forwarded_from = message.forward_from
        self.logger.info(
            f"Админ {message.from_user.id} переслал сообщение от пользователя: {forwarded_from.id}")

        try:
            user_id = forwarded_from.id
            username = forwarded_from.username
            first_name = forwarded_from.first_name or ""
            last_name = forwarded_from.last_name or ""

            # Проверяем, существует ли уже пользователь
            if await self.user_handler.user_exists(user_id):
                self.logger.warning(
                    f"Попытка добавить существующего пользователя {user_id} через пересланное сообщение")

                # Создаем клавиатуру с кнопкой "Назад"
                keyboard = InlineKeyboardBuilder()
                keyboard.button(text="⬅️ Назад", callback_data="back_to_admin")
                keyboard.adjust(1)

                await message.answer(
                    f"❌ Пользователь уже существует в системе.\n\n"
                    f"**ID:** `{user_id}`\n"
                    f"**Username:** @{username if username else 'не указан'}\n"
                    f"**Имя:** {first_name} {last_name}\n\n"
                    "Попробуйте другого пользователя:",
                    reply_markup=keyboard.as_markup(),
                    parse_mode="Markdown"
                )
                return

            # Сохраняем данные пользователя в состоянии
            await state.update_data(
                user_id=user_id,
                username=username,
                first_name=first_name,
                last_name=last_name
            )
            self.logger.debug(f"Данные пользователя {user_id} сохранены в состоянии")

            # Если у пользователя есть username, переходим сразу к выбору роли
            if username:
                await self._ask_for_role(message, state, user_id, username, first_name, last_name)
            else:
                # Если username нет, запрашиваем его
                await self._ask_for_username(message, state, user_id, first_name, last_name)

        except Exception as e:
            self.logger.error(f"Ошибка при обработке пересланного сообщения: {str(e)}", exc_info=True)
            await message.answer("❌ Произошла ошибка при обработке пересланного сообщения.")

    async def _ask_for_username(self, message: Message, state: FSMContext, user_id: int = None, first_name: str = "",
                                last_name: str = "") -> None:
        """
        Запрос username у администратора
        """
        # Если user_id передан, обновляем состояние
        if user_id:
            data = await state.get_data()
            data['user_id'] = user_id
            data['first_name'] = first_name
            data['last_name'] = last_name
            await state.set_data(data)

        # Создаем клавиатуру с кнопкой "Назад"
        keyboard = InlineKeyboardBuilder()
        keyboard.button(text="⬅️ Назад к вводу", callback_data="back_to_user_input")
        keyboard.adjust(1)

        current_data = await state.get_data()
        user_id = current_data.get('user_id')

        text = f"✅ ID пользователя: `{user_id}`\n\n"
        if first_name or last_name:
            text += f"**Имя:** {first_name} {last_name}\n\n"
        text += "Теперь введите username пользователя (без @). Если username отсутствует, отправьте '-' :"

        await message.answer(
            text,
            reply_markup=keyboard.as_markup(),
            parse_mode="Markdown"
        )
        await state.set_state(AdminStates.waiting_for_username)
        self.logger.debug(f"Установлено состояние waiting_for_username для админа {message.from_user.id}")

    async def _ask_for_role(self, message: Message, state: FSMContext, user_id: int, username: str, first_name: str,
                            last_name: str) -> None:
        """
        Запрос роли у администратора
        """
        # Сохраняем username в состоянии
        await state.update_data(username=username)

        # Создаем клавиатуру для выбора роли с кнопкой "Назад"
        keyboard = InlineKeyboardBuilder()
        keyboard.button(text="👤 Обычный пользователь", callback_data="role_user")
        keyboard.button(text="🛠️ Администратор", callback_data="role_admin")
        keyboard.button(text="⬅️ Назад к username", callback_data="back_to_username")
        keyboard.button(text="❌ Отмена", callback_data="cancel_operation")
        keyboard.adjust(2, 1, 1)

        text = f"✅ Данные пользователя:\n\n"
        text += f"**ID:** `{user_id}`\n"
        text += f"**Username:** @{username}\n"
        if first_name or last_name:
            text += f"**Имя:** {first_name} {last_name}\n"
        text += f"\nТеперь выберите роль пользователя:"

        await message.answer(
            text,
            reply_markup=keyboard.as_markup(),
            parse_mode="Markdown"
        )
        await state.set_state(AdminStates.waiting_for_role)
        self.logger.debug(f"Установлено состояние waiting_for_role для админа {message.from_user.id}")

    async def process_username(self, message: Message, state: FSMContext) -> None:
        """
        Обработка введенного username
        """
        username = message.text.strip()
        self.logger.debug(f"Обработка username от админа {message.from_user.id}: {username}")

        try:
            if username == "-":
                username = None
                self.logger.debug("Username установлен как None")
            else:
                # Убираем @ если пользователь его ввел
                username = username.lstrip('@')
                self.logger.debug(f"Username после обработки: {username}")

                # Проверяем валидность username
                if not self._is_valid_username(username):
                    self.logger.warning(f"Неверный формат username от админа {message.from_user.id}: {username}")

                    # Создаем клавиатуру с кнопкой "Назад"
                    keyboard = InlineKeyboardBuilder()
                    keyboard.button(text="⬅️ Назад к вводу", callback_data="back_to_user_input")
                    keyboard.adjust(1)

                    await message.answer(
                        "❌ Неверный формат username. Используйте только латинские буквы, цифры и подчеркивания.\n\n"
                        "Введите username еще раз или отправьте '-' если username отсутствует:",
                        reply_markup=keyboard.as_markup()
                    )
                    return

            await state.update_data(username=username)
            self.logger.debug(f"Username {username} сохранен в состоянии")

            # Получаем данные из состояния
            data = await state.get_data()
            user_id = data.get('user_id')
            first_name = data.get('first_name', '')
            last_name = data.get('last_name', '')

            # Переходим к выбору роли
            await self._ask_for_role(message, state, user_id, username, first_name, last_name)

        except Exception as e:
            self.logger.error(f"Ошибка при обработке username: {str(e)}", exc_info=True)

            # Создаем клавиатуру с кнопкой "Назад"
            keyboard = InlineKeyboardBuilder()
            keyboard.button(text="⬅️ Назад к вводу", callback_data="back_to_user_input")
            keyboard.adjust(1)

            await message.answer(
                "❌ Произошла ошибка при обработке username.",
                reply_markup=keyboard.as_markup()
            )

    async def back_to_user_input(self, callback: CallbackQuery, state: FSMContext) -> None:
        """
        Возврат к вводу пользователя
        """
        self.logger.info(f"Админ {callback.from_user.id} нажал 'Назад к вводу'")

        # Создаем клавиатуру с кнопкой "Назад"
        keyboard = InlineKeyboardBuilder()
        keyboard.button(text="⬅️ Назад", callback_data="back_to_admin")
        keyboard.adjust(1)

        await callback.message.edit_text(
            "👤 **Добавление нового пользователя**\n\n"
            "Вы можете:\n"
            "• Ввести ID пользователя (только цифры)\n"
            "• Переслать сообщение от пользователя\n\n"
            "Отправьте ID или перешлите сообщение:",
            reply_markup=keyboard.as_markup()
        )
        await state.set_state(AdminStates.waiting_for_user_input)
        await callback.answer()

    async def back_to_username_input(self, callback: CallbackQuery, state: FSMContext) -> None:
        """
        Возврат к вводу username
        """
        self.logger.info(f"Админ {callback.from_user.id} нажал 'Назад к username'")

        # Получаем сохраненные данные из состояния
        data = await state.get_data()
        user_id = data.get('user_id')
        first_name = data.get('first_name', '')
        last_name = data.get('last_name', '')

        # Создаем клавиатуру с кнопкой "Назад"
        keyboard = InlineKeyboardBuilder()
        keyboard.button(text="⬅️ Назад к вводу", callback_data="back_to_user_input")
        keyboard.adjust(1)

        text = f"✅ ID пользователя: `{user_id}`\n\n"
        if first_name or last_name:
            text += f"**Имя:** {first_name} {last_name}\n\n"
        text += "Теперь введите username пользователя (без @). Если username отсутствует, отправьте '-' :"

        await callback.message.edit_text(
            text,
            reply_markup=keyboard.as_markup(),
            parse_mode="Markdown"
        )
        await state.set_state(AdminStates.waiting_for_username)
        await callback.answer()

    async def delete_users_callback(self, callback: CallbackQuery) -> None:
        """
        Обработка нажатия кнопки "Удалить пользователя"
        """
        self.logger.info(f"Админ {callback.from_user.id} нажал кнопку 'Удалить пользователя'")

        try:
            # Получаем список всех пользователей
            users = await self.user_handler.get_all_users()

            if not users:
                await callback.message.edit_text(
                    "🗑️ **Удаление пользователей**\n\n"
                    "❌ Пользователи не найдены.",
                    reply_markup=InlineKeyboardBuilder()
                    .button(text="⬅️ Назад", callback_data="back_to_admin")
                    .adjust(1)
                    .as_markup()
                )
                return

            # Создаем клавиатуру с пользователями для удаления
            keyboard = InlineKeyboardBuilder()

            for user in users:
                # Админ не может удалить другого админа
                if user['role'] == UserRole.ADMIN:
                    continue

                username = f"@{user['username']}" if user['username'] else "без username"
                keyboard.button(
                    text=f"🗑️ {user['first_name']} {user['last_name']} ({username})",
                    callback_data=f"delete_user_{user['user_id']}"
                )

            keyboard.button(text="⬅️ Назад", callback_data="back_to_admin")
            keyboard.adjust(1)

            await callback.message.edit_text(
                "🗑️ **Удаление пользователей**\n\n"
                "Выберите пользователя для удаления:\n"
                "⚠️ *Администраторы не могут быть удалены*",
                reply_markup=keyboard.as_markup(),
                parse_mode="Markdown"
            )

        except Exception as e:
            self.logger.error(f"Ошибка при отображении списка для удаления: {str(e)}", exc_info=True)
            await callback.answer("❌ Ошибка при загрузке списка пользователей.")

    async def delete_user_callback(self, callback: CallbackQuery, state: FSMContext) -> None:
        """
        Обработка выбора пользователя для удаления
        """
        try:
            # Извлекаем ID пользователя из callback data
            user_id = int(callback.data.split("_")[2])
            self.logger.info(f"Админ {callback.from_user.id} выбрал для удаления пользователя {user_id}")

            # Получаем информацию о пользователе
            user_exists = await self.user_handler.user_exists(user_id)
            if not user_exists:
                await callback.answer("❌ Пользователь не найден.")
                return

            user_role = await self.user_handler.get_user_role(user_id)

            # Проверяем, что пользователь не админ
            if user_role == UserRole.ADMIN:
                await callback.answer("❌ Нельзя удалить администратора.")
                return

            # Сохраняем данные в состоянии для подтверждения
            await state.update_data(delete_user_id=user_id)

            # Создаем клавиатуру подтверждения
            keyboard = InlineKeyboardBuilder()
            keyboard.button(text="✅ Да, удалить", callback_data=f"confirm_delete_{user_id}")
            keyboard.button(text="❌ Отмена", callback_data=f"cancel_delete_{user_id}")
            keyboard.adjust(2)

            await callback.message.edit_text(
                f"🗑️ **Подтверждение удаления**\n\n"
                f"Вы уверены, что хотите удалить пользователя?\n"
                f"**ID:** `{user_id}`\n"
                f"**Роль:** {user_role.value}\n\n"
                f"⚠️ *Это действие нельзя отменить*",
                reply_markup=keyboard.as_markup(),
                parse_mode="Markdown"
            )
            await state.set_state(AdminStates.waiting_for_delete_confirmation)

        except Exception as e:
            self.logger.error(f"Ошибка при выборе пользователя для удаления: {str(e)}", exc_info=True)
            await callback.answer("❌ Ошибка при выборе пользователя.")

    async def confirm_delete_callback(self, callback: CallbackQuery, state: FSMContext) -> None:
        """
        Подтверждение удаления пользователя
        """
        try:
            # Извлекаем ID пользователя из callback data
            user_id = int(callback.data.split("_")[2])
            self.logger.info(f"Админ {callback.from_user.id} подтвердил удаление пользователя {user_id}")

            # Дополнительная проверка - получаем данные из состояния
            data = await state.get_data()
            state_user_id = data.get('delete_user_id')

            if state_user_id != user_id:
                self.logger.error(f"Несоответствие ID пользователя в состоянии: {state_user_id} != {user_id}")
                await callback.answer("❌ Ошибка: несоответствие данных.")
                return

            # Проверяем, что пользователь все еще существует и не админ
            user_exists = await self.user_handler.user_exists(user_id)
            if not user_exists:
                await callback.message.edit_text(
                    "❌ Пользователь не найден.",
                    reply_markup=InlineKeyboardBuilder()
                    .button(text="⬅️ Назад", callback_data="back_to_admin")
                    .adjust(1)
                    .as_markup()
                )
                await state.clear()
                return

            user_role = await self.user_handler.get_user_role(user_id)
            if user_role == UserRole.ADMIN:
                await callback.message.edit_text(
                    "❌ Нельзя удалить администратора.",
                    reply_markup=InlineKeyboardBuilder()
                    .button(text="⬅️ Назад", callback_data="back_to_admin")
                    .adjust(1)
                    .as_markup()
                )
                await state.clear()
                return

            # Удаляем пользователя из БД
            # Нужно добавить метод delete_user в DatabaseUserHandler
            result = await self.user_handler.delete_user(user_id)

            if result == ErrorCode.SUCCESSFUL:
                await callback.message.edit_text(
                    f"✅ **Пользователь успешно удален!**\n\n"
                    f"**ID:** `{user_id}`\n"
                    f"**Роль:** {user_role.value}",
                    reply_markup=InlineKeyboardBuilder()
                    .button(text="⬅️ В админ-панель", callback_data="back_to_admin")
                    .adjust(1)
                    .as_markup(),
                    parse_mode="Markdown"
                )

                # Логируем действие
                admin_username = f"@{callback.from_user.username}" if callback.from_user.username else callback.from_user.full_name
                self.logger.info(
                    f"Администратор {admin_username} ({callback.from_user.id}) "
                    f"удалил пользователя {user_id}"
                )
            else:
                await callback.message.edit_text(
                    "❌ **Ошибка при удалении пользователя!**\n\n"
                    "Попробуйте еще раз или обратитесь к разработчику.",
                    reply_markup=InlineKeyboardBuilder()
                    .button(text="⬅️ Назад", callback_data="back_to_admin")
                    .adjust(1)
                    .as_markup()
                )

            await state.clear()

        except Exception as e:
            self.logger.error(f"Ошибка при подтверждении удаления: {str(e)}", exc_info=True)
            await callback.message.edit_text(
                "❌ Произошла ошибка при удалении пользователя.",
                reply_markup=InlineKeyboardBuilder()
                .button(text="⬅️ Назад", callback_data="back_to_admin")
                .adjust(1)
                .as_markup()
            )
            await state.clear()

    async def cancel_delete_callback(self, callback: CallbackQuery, state: FSMContext) -> None:
        """
        Отмена удаления пользователя
        """
        self.logger.info(f"Админ {callback.from_user.id} отменил удаление пользователя")
        await state.clear()

        # Возвращаемся к списку пользователей для удаления
        await self.delete_users_callback(callback)

    async def process_delete_confirmation(self, message: Message, state: FSMContext) -> None:
        """
        Обработка текстового подтверждения удаления (если нужно)
        """
        await message.answer(
            "❌ Пожалуйста, используйте кнопки для подтверждения удаления.",
            reply_markup=InlineKeyboardBuilder()
            .button(text="⬅️ Назад", callback_data="back_to_admin")
            .adjust(1)
            .as_markup()
        )

    async def users_list_callback(self, callback: CallbackQuery) -> None:
        """
        Обработка нажатия кнопки "Список пользователей" - ЕДИНСТВЕННЫЙ способ посмотреть список
        """
        self.logger.info(f"Админ {callback.from_user.id} нажал кнопку 'Список пользователей'")

        try:
            users = await self.user_handler.get_all_users()
            self.logger.debug(f"Получено {len(users)} пользователей из БД")

            # Создаем клавиатуру с кнопкой "Назад"
            keyboard = InlineKeyboardBuilder()
            keyboard.button(text="⬅️ Назад", callback_data="back_to_admin")
            keyboard.adjust(1)

            if not users:
                await callback.message.edit_text(
                    "📋 **Список пользователей**\n\nПользователи не найдены.",
                    reply_markup=keyboard.as_markup()
                )
                self.logger.info("Список пользователей пуст")
            else:
                user_list = []
                for i, user in enumerate(users, 1):
                    username = f"@{user['username']}" if user['username'] else "нет"
                    last_name = user.get('last_name') or ""
                    first_name = f"{user['first_name']} {last_name}"
                    role_icon = "🛠️" if user['role'] == UserRole.ADMIN else "👤"
                    role_text = "Админ" if user['role'] == UserRole.ADMIN else "Пользователь"

                    user_list.append(
                        f"{i}. {role_icon} ID: `{user['user_id']}` | {username} | {first_name} | {role_text}"
                    )

                users_text = "\n".join(user_list)

                await callback.message.edit_text(
                    f"📋 **Список пользователей**\n\n"
                    f"Всего пользователей: {len(users)}\n\n"
                    f"{users_text}",
                    reply_markup=keyboard.as_markup(),
                    parse_mode="Markdown"
                )
                self.logger.info(f"Список из {len(users)} пользователей отправлен админу {callback.from_user.id}")

            await callback.answer()

        except Exception as e:
            self.logger.error(f"Ошибка при обработке callback списка пользователей: {str(e)}", exc_info=True)
            await callback.answer("❌ Ошибка при получении списка пользователей.")

    async def add_user_by_forward(self, message: Message, state: FSMContext) -> None:
        """
        Добавление пользователя по пересланному сообщению
        """
        forwarded_from = message.forward_from
        self.logger.info(
            f"Админ {message.from_user.id} пытается добавить пользователя по пересланному сообщению: {forwarded_from.id}")

        if not forwarded_from:
            await message.answer("❌ Не удалось получить информацию о пользователе из пересланного сообщения.")
            return

        try:
            user_id = forwarded_from.id
            username = forwarded_from.username
            first_name = forwarded_from.first_name or ""
            last_name = forwarded_from.last_name or ""

            # Проверяем, существует ли уже пользователь
            if await self.user_handler.user_exists(user_id):
                self.logger.warning(
                    f"Попытка добавить существующего пользователя {user_id} через пересланное сообщение")

                # Создаем клавиатуру с кнопкой "Назад"
                keyboard = InlineKeyboardBuilder()
                keyboard.button(text="⬅️ В админ-панель", callback_data="back_to_admin")
                keyboard.adjust(1)

                await message.answer(
                    f"❌ Пользователь уже существует в системе.\n\n"
                    f"**ID:** `{user_id}`\n"
                    f"**Username:** @{username if username else 'не указан'}\n"
                    f"**Имя:** {first_name} {last_name}",
                    reply_markup=keyboard.as_markup(),
                    parse_mode="Markdown"
                )
                return

            # Сохраняем данные пользователя в состоянии для быстрого доступа
            await state.update_data(
                quick_user_id=user_id,
                quick_username=username,
                quick_first_name=first_name,
                quick_last_name=last_name
            )

            # Создаем клавиатуру для быстрого добавления
            keyboard = InlineKeyboardBuilder()
            keyboard.button(text="👤 Добавить как пользователя", callback_data=f"quick_add_user_{user_id}")
            keyboard.button(text="🛠️ Добавить как админа", callback_data=f"quick_add_admin_{user_id}")
            keyboard.button(text="❌ Отмена", callback_data="cancel_operation")
            keyboard.adjust(1)

            await message.answer(
                f"👤 **Обнаружен пользователь из пересланного сообщения**\n\n"
                f"**ID:** `{user_id}`\n"
                f"**Username:** @{username if username else 'не указан'}\n"
                f"**Имя:** {first_name} {last_name}\n\n"
                f"Выберите роль для добавления:",
                reply_markup=keyboard.as_markup(),
                parse_mode="Markdown"
            )

        except Exception as e:
            self.logger.error(f"Ошибка при обработке пересланного сообщения: {str(e)}", exc_info=True)
            await message.answer("❌ Произошла ошибка при обработке пересланного сообщения.")

    async def process_user_id(self, message: Message, state: FSMContext) -> None:
        """
        Обработка введенного ID пользователя
        """
        self.logger.debug(f"Обработка ID пользователя от админа {message.from_user.id}: {message.text}")

        try:
            user_id = int(message.text.strip())
            self.logger.info(f"Админ {message.from_user.id} ввел ID пользователя: {user_id}")

            # Проверяем, существует ли уже пользователь
            if await self.user_handler.user_exists(user_id):
                self.logger.warning(f"Попытка добавить существующего пользователя {user_id}")

                # Создаем клавиатуру с кнопкой "Назад"
                keyboard = InlineKeyboardBuilder()
                keyboard.button(text="⬅️ Назад", callback_data="back_to_admin")
                keyboard.adjust(1)

                await message.answer(
                    "❌ Пользователь с таким ID уже существует в системе.\n\n"
                    "Хотите добавить другого пользователя? Введите новый ID:",
                    reply_markup=keyboard.as_markup()
                )
                return

            # Сохраняем ID в состоянии
            await state.update_data(user_id=user_id)
            self.logger.debug(f"ID пользователя {user_id} сохранен в состоянии")

            # Создаем клавиатуру с кнопкой "Назад"
            keyboard = InlineKeyboardBuilder()
            keyboard.button(text="⬅️ Назад к ID", callback_data="back_to_user_id")
            keyboard.adjust(1)

            await message.answer(
                "✅ ID пользователя принят.\n\n"
                "Теперь введите username пользователя (без @). "
                "Если username отсутствует, отправьте '-' :",
                reply_markup=keyboard.as_markup()
            )
            await state.set_state(AdminStates.waiting_for_username)
            self.logger.debug(f"Установлено состояние waiting_for_username для админа {message.from_user.id}")

        except ValueError:
            self.logger.warning(f"Неверный формат ID от админа {message.from_user.id}: {message.text}")

            # Создаем клавиатуру с кнопкой "Назад"
            keyboard = InlineKeyboardBuilder()
            keyboard.button(text="⬅️ Назад", callback_data="back_to_admin")
            keyboard.adjust(1)

            await message.answer(
                "❌ Неверный формат ID. Введите только цифры:\n"
                "Пример: 123456789",
                reply_markup=keyboard.as_markup()
            )
        except Exception as e:
            self.logger.error(f"Ошибка при обработке ID пользователя: {str(e)}", exc_info=True)

            # Создаем клавиатуру с кнопкой "Назад"
            keyboard = InlineKeyboardBuilder()
            keyboard.button(text="⬅️ Назад", callback_data="back_to_admin")
            keyboard.adjust(1)

            await message.answer(
                "❌ Произошла ошибка при обработке ID пользователя.",
                reply_markup=keyboard.as_markup()
            )

    # async def process_username(self, message: Message, state: FSMContext) -> None:
    #     """
    #     Обработка введенного username
    #     """
    #     username = message.text.strip()
    #     self.logger.debug(f"Обработка username от админа {message.from_user.id}: {username}")
    #
    #     try:
    #         if username == "-":
    #             username = None
    #             self.logger.debug("Username установлен как None")
    #         else:
    #             # Убираем @ если пользователь его ввел
    #             username = username.lstrip('@')
    #             self.logger.debug(f"Username после обработки: {username}")
    #
    #             # Проверяем валидность username
    #             if not self._is_valid_username(username):
    #                 self.logger.warning(f"Неверный формат username от админа {message.from_user.id}: {username}")
    #
    #                 # Создаем клавиатуру с кнопкой "Назад"
    #                 keyboard = InlineKeyboardBuilder()
    #                 keyboard.button(text="⬅️ Назад к ID", callback_data="back_to_user_id")
    #                 keyboard.adjust(1)
    #
    #                 await message.answer(
    #                     "❌ Неверный формат username. Используйте только латинские буквы, цифры и подчеркивания.\n\n"
    #                     "Введите username еще раз или отправьте '-' если username отсутствует:",
    #                     reply_markup=keyboard.as_markup()
    #                 )
    #                 return
    #
    #         await state.update_data(username=username)
    #         self.logger.debug(f"Username {username} сохранен в состоянии")
    #
    #         # Создаем клавиатуру для выбора роли с кнопкой "Назад"
    #         keyboard = InlineKeyboardBuilder()
    #         keyboard.button(text="👤 Обычный пользователь", callback_data="role_user")
    #         keyboard.button(text="🛠️ Администратор", callback_data="role_admin")
    #         keyboard.button(text="⬅️ Назад к username", callback_data="back_to_username")
    #         keyboard.button(text="❌ Отмена", callback_data="cancel_operation")
    #         keyboard.adjust(2, 1, 1)
    #
    #         await message.answer(
    #             "✅ Username принят.\n\n"
    #             "Теперь выберите роль пользователя:",
    #             reply_markup=keyboard.as_markup()
    #         )
    #         await state.set_state(AdminStates.waiting_for_role)
    #         self.logger.debug(f"Установлено состояние waiting_for_role для админа {message.from_user.id}")
    #
    #     except Exception as e:
    #         self.logger.error(f"Ошибка при обработке username: {str(e)}", exc_info=True)
    #
    #         # Создаем клавиатуру с кнопкой "Назад"
    #         keyboard = InlineKeyboardBuilder()
    #         keyboard.button(text="⬅️ Назад к ID", callback_data="back_to_user_id")
    #         keyboard.adjust(1)
    #
    #         await message.answer(
    #             "❌ Произошла ошибка при обработке username.",
    #             reply_markup=keyboard.as_markup()
    #         )

    async def process_quick_add_callback(self, callback: CallbackQuery, state: FSMContext) -> None:
        """
        Обработка быстрого добавления пользователя из пересланного сообщения
        """
        self.logger.debug(f"Обработка быстрого добавления от админа {callback.from_user.id}: {callback.data}")

        try:
            # Разбираем callback data: quick_add_user_123456 или quick_add_admin_123456
            parts = callback.data.split('_')
            role_str = parts[2]  # user или admin
            user_id = int(parts[3])

            role = UserRole.USER if role_str == "user" else UserRole.ADMIN
            self.logger.info(
                f"Админ {callback.from_user.id} быстрого добавляет пользователя {user_id} с ролью {role.value}")

            # Получаем сохраненные данные пользователя
            data = await state.get_data()
            username = data.get('quick_username')
            first_name = data.get('quick_first_name', 'Пользователь')
            last_name = data.get('quick_last_name', '')

            # Добавляем пользователя в БД
            result = await self.user_handler.add_user(
                user_id=user_id,
                username=username,
                first_name=first_name,
                last_name=last_name,
                role=role
            )

            # Создаем клавиатуру с кнопкой "Назад в админ-панель"
            keyboard = InlineKeyboardBuilder()
            keyboard.button(text="⬅️ В админ-панель", callback_data="back_to_admin")
            keyboard.adjust(1)

            if result == ErrorCode.SUCCESSFUL:
                role_text = "обычного пользователя" if role == UserRole.USER else "администратора"
                await callback.message.edit_text(
                    f"✅ **Пользователь успешно добавлен!**\n\n"
                    f"**ID:** `{user_id}`\n"
                    f"**Username:** {'@' + username if username else 'не указан'}\n"
                    f"**Имя:** {first_name} {last_name}\n"
                    f"**Роль:** {role_text}\n\n"
                    f"Пользователь теперь имеет доступ к боту.",
                    reply_markup=keyboard.as_markup(),
                    parse_mode="Markdown"
                )

                # Логируем действие
                admin_username = f"@{callback.from_user.username}" if callback.from_user.username else callback.from_user.full_name
                self.logger.info(
                    f"Администратор {admin_username} ({callback.from_user.id}) "
                    f"успешно добавил пользователя {user_id} с ролью {role.value} (быстрое добавление)"
                )
            else:
                self.logger.error(f"Ошибка при быстром добавлении пользователя {user_id}: {result}")
                await callback.message.edit_text(
                    "❌ **Ошибка при добавлении пользователя!**\n\n"
                    "Попробуйте еще раз или обратитесь к разработчику.",
                    reply_markup=keyboard.as_markup(),
                    parse_mode="Markdown"
                )

            await state.clear()
            await callback.answer()

        except Exception as e:
            self.logger.error(f"Ошибка при быстром добавлении пользователя: {str(e)}", exc_info=True)
            await callback.answer("❌ Ошибка при добавлении пользователя.")

    async def process_role_callback(self, callback: CallbackQuery, state: FSMContext) -> None:
        """
        Обработка выбора роли через callback
        """
        self.logger.debug(f"Обработка callback выбора роли от админа {callback.from_user.id}: {callback.data}")

        try:
            role_str = callback.data.split("_")[1]  # role_user или role_admin
            role = UserRole.USER if role_str == "user" else UserRole.ADMIN
            self.logger.info(f"Админ {callback.from_user.id} выбрал роль: {role.value}")

            # Получаем данные из состояния
            data = await state.get_data()
            user_id = data.get('user_id')
            username = data.get('username')
            first_name = data.get("first_name")
            last_name = data.get("last_name")

            self.logger.debug(f"Данные из состояния: user_id={user_id}, username={username}")

            if not user_id:
                self.logger.error("Не найден user_id в состоянии")
                await callback.message.edit_text("❌ Ошибка: данные сессии утеряны. Начните заново.")
                await state.clear()
                return

            # Добавляем пользователя в БД
            self.logger.info(f"Попытка добавления пользователя {user_id} с ролью {role.value}")
            result = await self.user_handler.add_user(
                user_id=user_id,
                username=username,
                first_name=first_name,  # Можно будет обновить позже
                last_name=last_name,
                role=role
            )

            # Создаем клавиатуру с кнопкой "Назад в админ-панель"
            keyboard = InlineKeyboardBuilder()
            keyboard.button(text="⬅️ В админ-панель", callback_data="back_to_admin")
            keyboard.adjust(1)

            if result == ErrorCode.SUCCESSFUL:
                role_text = "обычного пользователя" if role == UserRole.USER else "администратора"
                await callback.message.edit_text(
                    f"✅ **Пользователь успешно добавлен!**\n\n"
                    f"**ID:** `{user_id}`\n"
                    f"**Username:** {'@' + username if username else 'не указан'}\n"
                    f"**Роль:** {role_text}\n\n"
                    f"Пользователь теперь имеет доступ к боту.",
                    reply_markup=keyboard.as_markup(),
                    parse_mode="Markdown"
                )

                # Логируем действие
                admin_username = f"@{callback.from_user.username}" if callback.from_user.username else callback.from_user.full_name
                self.logger.info(
                    f"Администратор {admin_username} ({callback.from_user.id}) "
                    f"успешно добавил пользователя {user_id} с ролью {role.value}"
                )
            else:
                self.logger.error(f"Ошибка при добавлении пользователя {user_id}: {result}")
                await callback.message.edit_text(
                    "❌ **Ошибка при добавлении пользователя!**\n\n"
                    "Попробуйте еще раз или обратитесь к разработчику.",
                    reply_markup=keyboard.as_markup(),
                    parse_mode="Markdown"
                )

            await state.clear()
            self.logger.debug(f"Состояние очищено для админа {callback.from_user.id}")
            await callback.answer()

        except Exception as e:
            self.logger.error(f"Ошибка при обработке выбора роли: {str(e)}", exc_info=True)
            await callback.message.edit_text("❌ Произошла ошибка при добавлении пользователя.")
            await state.clear()
            await callback.answer()

    async def process_role(self, message: Message, state: FSMContext) -> None:
        """
        Обработка введенной роли (текстовый ввод)
        """
        role_text = message.text.strip().lower()
        self.logger.debug(f"Обработка текстового ввода роли от админа {message.from_user.id}: {role_text}")

        try:
            if role_text in ['user', 'пользователь', 'обычный']:
                role = UserRole.USER
            elif role_text in ['admin', 'админ', 'администратор']:
                role = UserRole.ADMIN
            else:
                self.logger.warning(f"Неверный ввод роли от админа {message.from_user.id}: {role_text}")

                # Создаем клавиатуру с кнопкой "Назад"
                keyboard = InlineKeyboardBuilder()
                keyboard.button(text="⬅️ Назад", callback_data="back_to_username")
                keyboard.adjust(1)

                await message.answer(
                    "❌ Неверная роль. Используйте:\n"
                    "- 'user' или 'пользователь' для обычного пользователя\n"
                    "- 'admin' или 'админ' для администратора",
                    reply_markup=keyboard.as_markup()
                )
                return

            self.logger.info(f"Админ {message.from_user.id} выбрал роль через текст: {role.value}")

            # Получаем данные из состояния
            data = await state.get_data()
            user_id = data.get('user_id')
            username = data.get('username')

            self.logger.debug(f"Данные из состояния: user_id={user_id}, username={username}")

            if not user_id:
                self.logger.error("Не найден user_id в состоянии")
                await message.answer("❌ Ошибка: данные сессии утеряны. Начните заново.")
                await state.clear()
                return

            # Добавляем пользователя в БД
            self.logger.info(f"Попытка добавления пользователя {user_id} с ролью {role.value}")
            result = await self.user_handler.add_user(
                user_id=user_id,
                username=username,
                first_name="Пользователь",
                last_name="",
                role=role
            )

            # Создаем клавиатуру с кнопкой "Назад в админ-панель"
            keyboard = InlineKeyboardBuilder()
            keyboard.button(text="⬅️ В админ-панель", callback_data="back_to_admin")
            keyboard.adjust(1)

            if result == ErrorCode.SUCCESSFUL:
                role_text = "обычного пользователя" if role == UserRole.USER else "администратора"
                await message.answer(
                    f"✅ **Пользователь успешно добавлен!**\n\n"
                    f"**ID:** `{user_id}`\n"
                    f"**:*Имя пользователя* {'@' + username if username else 'не указан'}\n"
                    f"**ФИО:** {username['first_name']} {username['last_name']}"
                    f"**Роль:** {role_text}\n\n"
                    f"Пользователь теперь имеет доступ к боту.",
                    reply_markup=keyboard.as_markup(),
                    parse_mode="Markdown"
                )

                # Логируем действие
                admin_username = f"@{message.from_user.username}" if message.from_user.username else message.from_user.full_name
                self.logger.info(
                    f"Администратор {admin_username} ({message.from_user.id}) "
                    f"успешно добавил пользователя {user_id} с ролью {role.value}"
                )
            else:
                self.logger.error(f"Ошибка при добавлении пользователя {user_id}: {result}")
                await message.answer(
                    "❌ **Ошибка при добавлении пользователя!**\n\n"
                    "Попробуйте еще раз или обратитесь к разработчику.",
                    reply_markup=keyboard.as_markup()
                )

            await state.clear()
            self.logger.debug(f"Состояние очищено для админа {message.from_user.id}")

        except Exception as e:
            self.logger.error(f"Ошибка при обработке текстовой роли: {str(e)}", exc_info=True)

            # Создаем клавиатуру с кнопкой "Назад"
            keyboard = InlineKeyboardBuilder()
            keyboard.button(text="⬅️ Назад к username", callback_data="back_to_username")
            keyboard.adjust(1)

            await message.answer(
                "❌ Произошла ошибка при добавлении пользователя.",
                reply_markup=keyboard.as_markup()
            )
            await state.clear()

    async def back_to_user_id_input(self, callback: CallbackQuery, state: FSMContext) -> None:
        """
        Возврат к вводу ID пользователя
        """
        self.logger.info(f"Админ {callback.from_user.id} нажал 'Назад к ID'")

        # Создаем клавиатуру с кнопкой "Назад"
        keyboard = InlineKeyboardBuilder()
        keyboard.button(text="⬅️ Назад", callback_data="back_to_admin")
        keyboard.adjust(1)

        await callback.message.edit_text(
            "👤 **Добавление нового пользователя**\n\n"
            "Введите ID пользователя (только цифры):",
            reply_markup=keyboard.as_markup()
        )
        await state.set_state(AdminStates.waiting_for_user_input)
        await callback.answer()

    async def cancel_operation(self, callback: CallbackQuery, state: FSMContext) -> None:
        """
        Отмена операции
        """
        self.logger.info(f"Админ {callback.from_user.id} отменил операцию")

        try:
            await state.clear()
            await callback.message.edit_text("❌ Операция отменена.")
            await callback.answer()
            self.logger.debug(f"Состояние очищено для админа {callback.from_user.id}")

        except Exception as e:
            self.logger.error(f"Ошибка при отмене операции: {str(e)}", exc_info=True)
            await callback.answer("❌ Ошибка при отмене операции.")

    def _is_valid_username(self, username: str) -> bool:
        """
        Проверяет валидность username
        """
        if not username:
            self.logger.debug("Username пустой - валидный")
            return True

        # Telegram username может содержать только a-z, 0-9 и _
        import re
        pattern = r'^[a-zA-Z0-9_]{5,32}$'
        is_valid = bool(re.match(pattern, username))

        if not is_valid:
            self.logger.debug(f"Username '{username}' не прошел валидацию")
        else:
            self.logger.debug(f"Username '{username}' прошел валидацию")

        return is_valid
