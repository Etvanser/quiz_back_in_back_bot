from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

from core.database_manager.db_users_handler import UserRole
from core.locale.locale import Locale


class AdminKeyboardBuilder:
    """
    Построение клавиатур для админ-панели
    """

    def __init__(self):
        self.locale = Locale()

    @property
    def admin_main_menu(self) -> InlineKeyboardMarkup:
        """
        Основное меню админ-панели - ПЕРВЫЙ УРОВЕНЬ
        """
        keyboard = InlineKeyboardBuilder()
        buttons = [
            (self.locale.buttons.get("btn_manage_users"), "manage_users_cmd"),
            (self.locale.buttons.get("btn_manage_players"), "manage_players_cmd"),
            (self.locale.buttons.get("btn_close"), "cancel_operation")
        ]

        for text, callback_data in buttons:
            keyboard.button(text=text, callback_data=callback_data)

        keyboard.adjust(1)
        return keyboard.as_markup()

    @property
    def admin_users_management_menu(self) -> InlineKeyboardMarkup:
        """
        Основное меню админ-панели
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

    @property
    def admin_players_management_menu(self) -> InlineKeyboardMarkup:
        """
        Клавиатура меню управления игроками
        """
        buttons = [
            [InlineKeyboardButton(text="➕ Добавить игрока", callback_data="add_player_cmd")],
            [InlineKeyboardButton(text="📋 Список игроков", callback_data="players_list_cmd")],
            [InlineKeyboardButton(text="🗑️ Удалить игрока", callback_data="delete_players_cmd")],
            [InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_admin")]
        ]
        return InlineKeyboardMarkup(inline_keyboard=buttons)

    @property
    def back_to_players_management_keyboard(self) -> InlineKeyboardMarkup:
        """
        Клавиатура для возврата в меню управления игроками
        """
        buttons = [
            [InlineKeyboardButton(text="◀️ Назад к управлению игроками", callback_data="manage_players_cmd")]
        ]
        return InlineKeyboardMarkup(inline_keyboard=buttons)

    @property
    def role_selection_keyboard(self) -> InlineKeyboardMarkup:
        """
        Клавиатура выбора роли
        """
        keyboard = InlineKeyboardBuilder()
        keyboard.button(text=self.locale.buttons.get("btn_role_user"), callback_data="role_user")
        keyboard.button(text=self.locale.buttons.get("btn_role_admin"), callback_data="role_admin")
        keyboard.button(text=self.locale.buttons.get("btn_back"), callback_data="add_user_cmd")
        keyboard.button(text=self.locale.buttons.get("btn_cancel"), callback_data="cancel_operation")
        keyboard.adjust(2, 1, 1)
        return keyboard.as_markup()

    # def create_user_list_keyboard(self, users: list[dict]) -> InlineKeyboardMarkup:
    #     """Клавиатура списка пользователей"""
    #     # ... реализация

    def create_confirmation_delete_user_keyboard(self, user_id: int) -> InlineKeyboardMarkup:
        """
        Клавиатура подтверждения удаления пользователя
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

    def create_single_button(self, text: str, callback_data: str) -> InlineKeyboardMarkup:
        """
        Кнопка назад
        """
        keyboard = InlineKeyboardBuilder()
        keyboard.button(text=text, callback_data=callback_data)
        keyboard.adjust(1)
        return keyboard.as_markup()

    def create_delete_user_list_keyboard(self, users: list[dict]) -> InlineKeyboardMarkup:
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

    def players_list_keyboard(self, players: list) -> InlineKeyboardMarkup:
        """Клавиатура для списка игроков"""
        buttons = []

        # Добавляем кнопки для каждого игрока
        for player in players:
            buttons.append([
                InlineKeyboardButton(
                    text=f"🗑️ {player.first_name} {player.last_name}",
                    callback_data=f"delete_player_{player.player_id}"
                )
            ])

        # Кнопка возврата
        buttons.append([
            InlineKeyboardButton(text="◀️ Назад", callback_data="manage_players_cmd")
        ])

        return InlineKeyboardMarkup(inline_keyboard=buttons)

    def players_delete_keyboard(self, players: list) -> InlineKeyboardMarkup:
        """
        Клавиатура для удаления игроков
        """
        buttons = []

        # Добавляем кнопки для каждого игрока
        for player in players:
            buttons.append([
                InlineKeyboardButton(
                    text=f"🗑️ {player.first_name} {player.last_name}",
                    callback_data=f"delete_player_{player.player_id}"
                )
            ])

        # Кнопка возврата
        buttons.append([
            InlineKeyboardButton(text="◀️ Назад", callback_data="manage_players_cmd")
        ])

        return InlineKeyboardMarkup(inline_keyboard=buttons)

    def confirm_delete_user_keyboard(self, user_id: int) -> InlineKeyboardMarkup:
        buttons = [
            [
                InlineKeyboardButton(
                    text=self.locale.buttons.get("btn_confirm_delete"),
                    callback_data=f"confirm_delete_user_{user_id}"
                ),
                InlineKeyboardButton(
                    text=self.locale.buttons.get("btn_cancel"),
                    callback_data="cancel_delete_user"
                )
            ]
        ]
        return InlineKeyboardMarkup(inline_keyboard=buttons)

    def confirm_delete_player_keyboard(self, player_id: int) -> InlineKeyboardMarkup:
        buttons = [
            [
                InlineKeyboardButton(
                    text=self.locale.buttons.get("btn_confirm_delete"),
                    callback_data=f"confirm_delete_player_{player_id}"
                ),
                InlineKeyboardButton(
                    text=self.locale.buttons.get("btn_cancel"),
                    callback_data="cancel_delete_player"
                )
            ]
        ]
        return InlineKeyboardMarkup(inline_keyboard=buttons)

    @property
    def photo_upload_keyboard(self) -> InlineKeyboardMarkup:
        """
        Создает клавиатуру для загрузки фото с кнопкой пропуска

        :return: InlineKeyboardMarkup с кнопками
        """
        buttons = [
            [InlineKeyboardButton(
                text=self.locale.buttons.get("btn_skip"),
                callback_data="skip_photo"
            )],
            [InlineKeyboardButton(
                text=self.locale.buttons.get("btn_cancel"),
                callback_data="cancel_operation"
            )]
        ]
        return InlineKeyboardMarkup(inline_keyboard=buttons)

    @property
    def nickname_skip_keyboard(self) -> InlineKeyboardMarkup:
        """
        Создает клавиатуру для ввода ника с кнопкой пропуска

        :return: InlineKeyboardMarkup с кнопками
        """
        buttons = [
            [InlineKeyboardButton(
                text=self.locale.buttons.get("btn_skip"),
                callback_data="skip_nickname"
            )],
            [InlineKeyboardButton(
                text=self.locale.buttons.get("btn_cancel"),
                callback_data="cancel_operation"
            )]
        ]
        return InlineKeyboardMarkup(inline_keyboard=buttons)
