from aiogram import Router, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup
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
        """
        Создает экземпляр класса AdminRouter

        :param router: Роутер aiogram для регистрации обработчиков
        """
        self.user_handler = DatabaseUserHandler()
        self.logger = Logger().get_logger()
        super().__init__(router)
        self.logger.info("AdminRouter инициализирован")

    def _create_admin_keyboard(self) -> InlineKeyboardMarkup:
        """
        Создает клавиатуру для админ-панели
        """
        keyboard = InlineKeyboardBuilder()

        buttons = [
            (self.locale.buttons.get("btn_add_user"), "add_user_cmd"),
            (self.locale.buttons.get("btn_list_users"), "users_list_cmd"),
            (self.locale.buttons.get("btn_delete_user"), "delete_users_cmd"),
            (self.locale.buttons.get("btn_close"), "cancel_operation")
        ]

        for text, callback_data in buttons:
            keyboard.button(text=text, callback_data=callback_data)

        keyboard.adjust(1)
        return keyboard.as_markup()

    def _back_button_keyboard(self, callback_data: str) -> InlineKeyboardMarkup:
        """
        Создает клавиатуру с кнопкой назад

        :param callback_data: Callback куда нужно вернутся
        """
        keyboard = InlineKeyboardBuilder()
        text = self.locale.buttons.get("btn_back")

        keyboard.button(text=text, callback_data=callback_data)
        keyboard.adjust(1)
        return keyboard.as_markup()

    async def _send_or_edit_message(
            self,
            target: Message | CallbackQuery,
            text: str,
            reply_markup: InlineKeyboardMarkup,
            parse_mode: str = "Markdown"
    ) -> None:
        """
        Универсальный метод для отправки или редактирования сообщения
        """
        if isinstance(target, Message):
            await target.answer(text, reply_markup=reply_markup, parse_mode=parse_mode)
        else:
            await target.message.edit_text(text, reply_markup=reply_markup, parse_mode=parse_mode)

    async def _is_admin(self, user_id: int) -> bool:
        """
        Проверяет, является ли пользователь администратором по данным из БД

        :param user_id: ID пользователя для проверки
        :return: True если пользователь администратор, иначе False
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
        self.router.message(Command("admin"))(self._admin_panel)

        # Обработчики состояний для добавления пользователя
        self.router.message(AdminStates.waiting_for_user_input)(self._process_user_input)
        self.router.message(AdminStates.waiting_for_role)(self.process_role)

        # Callback-обработчики для кнопок
        self.router.callback_query(F.data == "add_user_cmd")(self._add_user_callback)
        self.router.callback_query(F.data == "users_list_cmd")(self.users_list_callback)
        self.router.callback_query(F.data == "delete_users_cmd")(self.delete_users_callback)
        self.router.callback_query(F.data.startswith("role_"))(self.process_role_callback)
        self.router.callback_query(F.data.startswith("quick_add_"))(self.process_quick_add_callback)
        self.router.callback_query(F.data.startswith("delete_user_"))(self.delete_user_callback)
        self.router.callback_query(F.data.startswith("confirm_delete_"))(self.confirm_delete_callback)
        self.router.callback_query(F.data.startswith("cancel_delete_"))(self.cancel_delete_callback)
        self.router.callback_query(F.data == "cancel_operation")(self.cancel_operation)
        self.router.callback_query(F.data == "back_to_admin")(self._back_to_admin_panel)

        self.logger.info("Обработчики AdminRouter успешно зарегистрированы")

    async def _admin_panel(self, target: Message | CallbackQuery) -> None:
        """
        Панель администратора - ЕДИНСТВЕННАЯ точка входа, проверяющая права

        :param target: Сообщение или callback запрос от пользователя
        """
        user_id = target.from_user.id
        message = target if isinstance(target, Message) else target.message

        if not await self._is_admin(user_id):
            await message.answer(self.locale.bot.get("access_denied_msg"))
            self.logger.warning(f"Попытка доступа к админ-панели от не-админа: {user_id}")
            return

        self.logger.info(f"Админ {user_id} вызвал панель администратора")

        try:
            keyboard = self._create_admin_keyboard()

            text = self.locale.ui.get("admin_panel_desc")
            await self._send_or_edit_message(target, text, keyboard)

            self.logger.debug(f"Панель администратора отправлена пользователю {user_id}")

        except Exception as e:
            self.logger.error(f"Ошибка при отображении панели администратора: {str(e)}", exc_info=True)
            await message.answer(self.locale.bot.get("error_display_admin_panel"))

    async def _back_to_admin_panel(self, callback: CallbackQuery, state: FSMContext) -> None:
        """
        Возврат в админ-панель

        :param callback: Callback запрос от кнопки
        :param state: Состояние FSM
        """
        self.logger.info(f"Админ {callback.from_user.id} нажал 'Назад в админ-панель'")
        await state.clear()
        await self._admin_panel(callback)
        await callback.answer()

    async def _add_user_callback(self, callback: CallbackQuery, state: FSMContext) -> None:
        """
        Обработка нажатия кнопки "Добавить пользователя" - ЕДИНСТВЕННЫЙ способ начать добавление

        :param callback: Callback запрос от кнопки
        :param state: Состояние FSM
        """
        self.logger.info(f"Админ {callback.from_user.id} нажал кнопку 'Добавить пользователя'")

        try:
            await state.clear()
            await self._send_or_edit_message(
                target=callback,
                text=self.locale.ui.get("add_user_desc"),
                reply_markup=self._back_button_keyboard(callback_data="back_to_admin")
            )

            await state.set_state(AdminStates.waiting_for_user_input)
            await callback.answer()

        except Exception as e:
            self.logger.error(f"Ошибка при обработке callback добавления пользователя: {str(e)}", exc_info=True)
            await callback.answer(self.locale.bot.get("error_add_user_msg"))

    async def _process_user_input(self, message: Message, state: FSMContext) -> None:
        """
        Обработка пересланного сообщение

        :param message: Сообщение от пользователя
        :param state: Состояние FSM
        """
        self.logger.debug(f"Обработка ввода от админа {message.from_user.id}: {message.text}")

        if not message.forward_from:
            await self._handle_invalid_input(message)
            return

        await self._handle_forwarded_message(message, state)

    async def _handle_invalid_input(self, message: Message) -> None:
        """
        Обработка некорректного ввода (не пересланное сообщение)
        """
        admin_id = message.from_user.id
        self.logger.warning(f"Админ {admin_id} отправил непересланное сообщение: {message.text}")

        text = self.locale.bot.get("error_input_forward_msg")
        await self._send_or_edit_message(
            target=message,
            text=text,
            reply_markup=self._back_button_keyboard(callback_data="back_to_admin")
        )

    async def _handle_forwarded_message(self, message: Message, state: FSMContext) -> None:
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
                await self._send_or_edit_message(
                    target=message,
                    text=text,
                    reply_markup=self._back_button_keyboard(callback_data="back_to_admin")
                )
                return

            await state.update_data(
                user_id=user_id,
                username=username,
                first_name=first_name,
                last_name=last_name
            )
            self.logger.debug(f"Данные пользователя {user_id} сохранены в состоянии")
            await self._ask_for_role(message, state, user_id, username, first_name, last_name)

        except Exception as e:
            self.logger.error(f"Ошибка при обработке пересланного сообщения: {str(e)}", exc_info=True)
            await message.answer("❌ Произошла ошибка при обработке пересланного сообщения.")

    async def _ask_for_role(
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

        keyboard = InlineKeyboardBuilder()
        keyboard.button(text=self.locale.buttons.get("btn_role_user"), callback_data="role_user")
        keyboard.button(text=self.locale.buttons.get("btn_role_admin"), callback_data="role_admin")
        keyboard.button(text=self.locale.buttons.get("btn_back"), callback_data="add_user_cmd")
        keyboard.button(text=self.locale.buttons.get("btn_cancel"), callback_data="cancel_operation")
        keyboard.adjust(2, 1, 1)

        text = self.locale.ui.get("add_user_data_desc").format(
            user_id=user_id,
            username=username if username else "не указан",
            first_name=first_name or "",
            last_name=last_name or "",
        )

        await self._send_or_edit_message(
            target=message,
            text=text,
            reply_markup=keyboard.as_markup()
        )
        await state.set_state(AdminStates.waiting_for_role)
        self.logger.debug(f"Установлено состояние waiting_for_role для админа {message.from_user.id}")

    def _create_delete_user_list_keyboard(self, users: list[dict]) -> InlineKeyboardMarkup:
        """
        Создает клавиатуру со списком пользователей для удаления
        """
        keyboard = InlineKeyboardBuilder()

        for user in users:
            if user.get("role") == UserRole.ADMIN:
                continue

            username = f"@{user['username']}" if user['username'] else "без username"
            keyboard.button(
                text=f"🗑️ {user['first_name']} {user['last_name']} ({username})",
                callback_data=f"delete_user_{user['user_id']}"
            )

        keyboard.button(text=self.locale.buttons.get("btn_back"), callback_data="back_to_admin")
        keyboard.adjust(1)
        return keyboard.as_markup()

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
                await self._send_or_edit_message(
                    target=callback,
                    text=text,
                    reply_markup=self._back_button_keyboard(callback_data="back_to_admin")
                )
                return

            text = self.locale.ui.get("delete_users_desc")
            await self._send_or_edit_message(
                target=callback,
                text=text,
                reply_markup=self._create_delete_user_list_keyboard(users)
            )

        except Exception as e:
            self.logger.error(f"Ошибка при отображении списка для удаления: {str(e)}", exc_info=True)
            await callback.answer(self.locale.bot.get("error_users_list"))

    def _create_yes_no_delete_user_keyboard(self, user_id: int) -> InlineKeyboardMarkup:
        """
        Создает клавиатуру с подтверждением удаления пользователя
        """
        keyboard = InlineKeyboardBuilder()

        buttons = [
            (self.locale.buttons.get("btn_yes_delete"), f"confirm_delete_{user_id}"),
            (self.locale.buttons.get("btn_cancel"), f"cancel_delete_{user_id}")
        ]

        for text, callback_data in buttons:
            keyboard.button(text=text, callback_data=callback_data)

        keyboard.adjust(2)
        return keyboard.as_markup()

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
            await self._send_or_edit_message(
                target=callback,
                text=text,
                reply_markup=self._create_yes_no_delete_user_keyboard(user_id)
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
                await self._send_or_edit_message(
                    target=callback,
                    text=self.locale.bot.get("error_user_not_found"),
                    reply_markup=self._back_button_keyboard(callback_data="back_to_admin")
                )
                await state.clear()
                return

            user_role = await self.user_handler.get_user_role(user_id)
            if user_role == UserRole.ADMIN:
                await self._send_or_edit_message(
                    target=callback,
                    text=self.locale.bot.get("error_delete_admin"),
                    reply_markup=self._back_button_keyboard(callback_data="back_to_admin")
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
                await self._send_or_edit_message(
                    target=callback,
                    text=text,
                    reply_markup=self._back_button_keyboard(callback_data="back_to_admin")
                )

                admin_username = f"@{callback.from_user.username}" if callback.from_user.username else callback.from_user.full_name
                self.logger.info(
                    f"Администратор {admin_username} ({callback.from_user.id}) "
                    f"удалил пользователя {user_id}"
                )
            else:
                await self._send_or_edit_message(
                    target=callback,
                    text=self.locale.bot.get("error_delete_user_desc"),
                    reply_markup=self._back_button_keyboard(callback_data="back_to_admin")
                )
            await state.clear()

        except Exception as e:
            self.logger.error(f"Ошибка при подтверждении удаления: {str(e)}", exc_info=True)
            await self._send_or_edit_message(
                target=callback,
                text=self.locale.bot.get("error_delete_user_desc"),
                reply_markup=self._back_button_keyboard(callback_data="back_to_admin")
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

        :param message: Пересланное сообщение
        :param state: Состояние FSM
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
