from aiogram import Router, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery

from core.database_manager.db_players_handler import DatabaseQuizPlayerHandler
from core.database_manager.db_users_handler import UserRole, DatabaseUserHandler
from core.router_recorder import RoutersRecorder
from core.routers import BaseRouter
from core.routers.admin_panel import AdminStates, AdminMessageSender, AdminKeyboardBuilder, PlayersManagerService
from core.routers.admin_panel.user_manager_service import UsersManagerService
from logger import Logger


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
        self.players_handler = DatabaseQuizPlayerHandler()
        self.keyboard = AdminKeyboardBuilder()
        self.user_manager = UsersManagerService(
            user_handler=self.user_handler,
            keyboard=self.keyboard
        )
        self.players_manager = PlayersManagerService(
            players_handler=self.players_handler,
            keyboard=self.keyboard
        )
        self.logger = Logger().get_logger()
        super().__init__(router)
        self.logger.info("AdminRouter инициализирован")

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

        # Обработчик возврата в админ панель
        self.router.callback_query(F.data == "back_to_admin")(self._back_to_admin_panel)
        self.router.callback_query(F.data == "cancel_operation")(self._cancel_operation)

        # Обработчики по работе с пользователями
        self._users_manager_handlers()
        #Обработчики по работе с игроками
        self._players_manager_handlers()

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
            await AdminMessageSender().send_or_edit_message(
                target=target,
                text=self.locale.ui.get("admin_panel_desc"),
                reply_markup=self.keyboard.admin_main_menu
            )
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

    async def _cancel_operation(self, callback: CallbackQuery, state: FSMContext) -> None:
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
            await callback.answer("❌ Ошибка при отмене операции.")\


    def _users_manager_handlers(self) -> None:
        """
        Обработчики по работе с users
        """
        self.router.callback_query(F.data == "manage_users_cmd")(self.user_manager.manage_users_panel)
        self.router.message(AdminStates.waiting_for_user_input)(self.user_manager.process_user_input)
        self.router.callback_query(F.data == "add_user_cmd")(self.user_manager.add_user_callback)
        self.router.callback_query(F.data == "users_list_cmd")(self.user_manager.users_list_callback)
        self.router.callback_query(F.data == "delete_users_cmd")(self.user_manager.delete_users_callback)
        self.router.callback_query(F.data.startswith("role_"))(self.user_manager.process_role_callback)
        self.router.callback_query(F.data.startswith("delete_user_"))(self.user_manager.delete_user_callback)
        self.router.callback_query(F.data.startswith("confirm_delete_user_"))(self.user_manager.confirm_delete_callback)
        self.router.callback_query(F.data.startswith("cancel_delete_user"))(self.user_manager.cancel_delete_callback)

    def _players_manager_handlers(self) -> None:
        """
        Обработчики по работе с игроками
        """
        self.router.callback_query(F.data == "manage_players_cmd")(self.players_manager.manage_players_panel)
        self.router.callback_query(F.data == "add_player_cmd")(self.players_manager.add_player_callback)
        self.router.callback_query(F.data == "players_list_cmd")(self.players_manager.players_list_callback)
        self.router.callback_query(F.data == "delete_players_cmd")(self.players_manager.delete_players_callback)
        self.router.callback_query(F.data == "cancel_player_operation")(self.players_manager.cancel_operation)
        self.router.callback_query(F.data.startswith("delete_player_"))(self.players_manager.delete_player_callback)
        self.router.callback_query(F.data.startswith("confirm_delete_player_"))(self.players_manager.confirm_delete_player_callback)
        self.router.callback_query(F.data == "cancel_delete_player")(self.players_manager.cancel_delete_player_callback)
        self.router.callback_query(F.data == "skip_photo")(self.players_manager.skip_photo_callback)
        self.router.callback_query(F.data == "skip_nickname")(self.players_manager.skip_nickname_callback)

        self.router.message(AdminStates.waiting_for_player_nickname)(self.players_manager.process_player_nickname_input)
        self.router.message(AdminStates.waiting_for_player_name)(self.players_manager.process_player_name_input)
        self.router.message(AdminStates.waiting_for_player_photo)(self.players_manager.process_player_photo_input)
        self.router.message(AdminStates.waiting_for_player_games)(self.players_manager.process_player_games_input)


