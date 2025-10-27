from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from core.database_manager.db_players_habdler import DatabaseQuizPlayerHandler
from core.locale.locale import Locale
from core.routers.admin_panel import AdminMessageSender, AdminKeyboardBuilder, AdminStates
from errors import ErrorCode
from logger import Logger


class PlayersManagerService:

    def __init__(self, players_handler: DatabaseQuizPlayerHandler, keyboard: AdminKeyboardBuilder):
        self.locale = Locale()
        self.logger = Logger().get_logger()
        self.keyboard = keyboard
        self.players_handler = players_handler


    async def manage_players_panel(self, callback: CallbackQuery, state: FSMContext) -> None:
        """
        Панель управления играками - ВТОРОЙ УРОВЕНЬ

        :param callback: Callback запрос от кнопки
        :param state: Состояние FSM
        """
        self.logger.info(f"Админ {callback.from_user.id} открыл панель управления играками")
        await state.clear()

        try:
            await AdminMessageSender().send_or_edit_message(
                target=callback,
                text=self.locale.ui.get("admin_players_management_desc"),
                reply_markup=self.keyboard.admin_players_management_menu
            )
        except Exception as e:
            self.logger.error(f"Ошибка при отображении панели управления играками: {str(e)}")
            await callback.message.answer(self.locale.bot.get("error_display_admin_panel"))

        await callback.answer()

    async def add_player_callback(self, callback: CallbackQuery, state: FSMContext) -> None:
        """
        Обработчик кнопки добавления игрока

        :param callback: Callback запрос от кнопки
        :param state: Состояние FSM
        """
        self.logger.info(f"Админ {callback.from_user.id} начал добавление игрока")

        try:
            await state.set_state(AdminStates.waiting_for_player_name)
            await state.update_data(player_data={})

            await AdminMessageSender().send_or_edit_message(
                target=callback,
                text=self.locale.ui.get("admin_add_player_name_desc"),
                reply_markup=self.keyboard.create_single_button(
                    text=self.locale.buttons.get("btn_cancel"),
                    callback_data="cancel_operation"
                )
            )

        except Exception as e:
            self.logger.error(f"Ошибка при начале добавления игрока: {str(e)}")
            await callback.message.answer(self.locale.bot.get("error_operation"))

        await callback.answer()

    async def process_player_name_input(self, message: Message, state: FSMContext) -> None:
        """
        Обработка ввода имени и фамилии игрока

        :param message: Сообщение с именем и фамилией
        :param state: Состояние FSM
        """
        user_id = message.from_user.id
        name_input = message.text.strip()

        try:
            # Проверяем формат ввода (должны быть имя и фамилия)
            name_parts = name_input.split()
            if len(name_parts) < 2:
                await message.answer(
                    self.locale.ui.get("admin_player_name_format_error"),
                    reply_markup=self.keyboard.create_single_button(
                        text=self.locale.buttons.get("btn_cancel"),
                        callback_data="cancel_operation"
                    )
                )
                return

            first_name = name_parts[0]
            last_name = ' '.join(name_parts[1:])

            # Сохраняем в состоянии
            await state.update_data(
                player_first_name=first_name,
                player_last_name=last_name
            )

            # Переходим к запросу фото
            await state.set_state(AdminStates.waiting_for_player_photo)

            await message.answer(
                self.locale.ui.get("admin_add_player_photo_desc"),
                reply_markup=self.keyboard.create_single_button(
                    text=self.locale.buttons.get("btn_cancel"),
                    callback_data="cancel_operation"
                )
            )

        except Exception as e:
            self.logger.error(f"Ошибка при обработке имени игрока: {str(e)}")
            await message.answer(
                self.locale.bot.get("error_operation"),
                reply_markup=self.keyboard.create_single_button(
                    text=self.locale.buttons.get("btn_cancel"),
                    callback_data="cancel_operation"
                )
            )

    async def process_player_photo_input(self, message: Message, state: FSMContext) -> None:
        """
        Обработка загрузки фото игрока

        :param message: Сообщение с фото
        :param state: Состояние FSM
        """
        user_id = message.from_user.id

        try:
            if not message.photo:
                await message.answer(
                    self.locale.ui.get("admin_player_photo_error"),
                    reply_markup=self.keyboard.create_single_button(
                        text=self.locale.buttons.get("btn_cancel"),
                        callback_data="cancel_operation"
                    )
                )
                return

            # Получаем самое большое фото
            photo = message.photo[-1]
            photo_file = await message.bot.get_file(photo.file_id)

            # Сохраняем информацию о фото
            await state.update_data(player_photo_file_id=photo_file.file_id)

            # Переходим к запросу количества игр
            await state.set_state(AdminStates.waiting_for_player_games)

            await message.answer(
                self.locale.ui.get("admin_add_player_games_desc"),
                reply_markup=self.keyboard.create_single_button(
                    text=self.locale.buttons.get("btn_cancel"),
                    callback_data="cancel_operation"
                )
            )

        except Exception as e:
            self.logger.error(f"Ошибка при обработке фото игрока: {str(e)}")
            await message.answer(
                self.locale.bot.get("error_operation"),
                reply_markup=self.keyboard.create_single_button(
                    text=self.locale.buttons.get("btn_cancel"),
                    callback_data="cancel_operation"
                )
            )

    async def process_player_games_input(self, message: Message, state: FSMContext) -> None:
        """
        Обработка ввода количества сыгранных игр

        :param message: Сообщение с количеством игр
        :param state: Состояние FSM
        """
        user_id = message.from_user.id
        games_input = message.text.strip()

        try:
            # Проверяем, что введено число
            try:
                games_played = int(games_input)
                if games_played < 0:
                    raise ValueError("Отрицательное число")
            except ValueError:
                await message.answer(
                    self.locale.ui.get("admin_player_games_format_error"),
                    reply_markup=self.keyboard.create_single_button(
                        text=self.locale.buttons.get("btn_cancel"),
                        callback_data="cancel_operation"
                    )
                )
                return

            # Получаем данные из состояния
            state_data = await state.get_data()
            first_name = state_data.get('player_first_name')
            last_name = state_data.get('player_last_name')
            photo_file_id = state_data.get('player_photo_file_id')

            if not first_name or not last_name:
                await message.answer(
                    self.locale.bot.get("error_operation"),
                    reply_markup=self.keyboard.create_single_button(
                        text=self.locale.buttons.get("btn_cancel"),
                        callback_data="cancel_operation"
                    )
                )
                await state.clear()
                return

            # Рассчитываем уровни на основе количества игр
            numeric_level = await self.players_handler.calculate_numeric_level_from_games(games_played)
            text_level = await self.players_handler.calculate_text_level_from_games(games_played)

            self.logger.info(f"Рассчитаны уровни для игрока: games={games_played}, "
                             f"numeric_level={numeric_level}, text_level={text_level}")

            # Сохраняем фото во временный файл
            photo_path = None
            if photo_file_id:
                photo_path = await self._download_photo(message.bot, photo_file_id, first_name, last_name)

            # Добавляем игрока в базу
            result = await self.players_handler.add_player(
                first_name=first_name,
                last_name=last_name,
                photo_path=photo_path,
                games_played=games_played,
                player_level=text_level,
                numeric_level=numeric_level
            )

            # Очищаем состояние
            await state.clear()

            # Отправляем результат
            if result == ErrorCode.SUCCESSFUL:
                await message.answer(
                    self.locale.ui.get("admin_player_add_success").format(
                        first_name=first_name,
                        last_name=last_name,
                        games_played=games_played,
                        level=text_level.value,
                        numeric_level=numeric_level
                    ),
                    reply_markup=self.keyboard.back_to_players_management_keyboard
                )
                self.logger.info(f"Игрок {first_name} {last_name} успешно добавлен")
            else:
                error_msg = self._get_error_message(result)
                await message.answer(
                    self.locale.bot.get("admin_player_add_error").format(error=error_msg),
                    reply_markup=self.keyboard.back_to_players_management_keyboard
                )
                self.logger.error(f"Ошибка добавления игрока: {error_msg}")

        except Exception as e:
            self.logger.error(f"Ошибка при обработке количества игр: {str(e)}")
            await message.answer(
                self.locale.bot.get("error_operation"),
                reply_markup=self.keyboard.back_to_players_management_keyboard
            )
            await state.clear()

    async def _download_photo(self, bot, file_id: str, first_name: str, last_name: str) -> str | None:
        """
        Скачивает фото и сохраняет во временный файл

        :param bot: Бот для скачивания
        :param file_id: ID файла в Telegram
        :param first_name: Имя игрока
        :param last_name: Фамилия игрока
        :return: Путь к сохраненному файлу
        """
        import tempfile
        import os

        try:
            # Создаем временный файл
            safe_first_name = "".join(c for c in first_name if c.isalnum() or c in (' ', '-', '_')).rstrip()
            safe_last_name = "".join(c for c in last_name if c.isalnum() or c in (' ', '-', '_')).rstrip()

            with tempfile.NamedTemporaryFile(
                    suffix='.jpg',
                    prefix=f'{safe_first_name}_{safe_last_name}_',
                    delete=False
            ) as temp_file:
                temp_path = temp_file.name

            # Скачиваем файл
            file = await bot.get_file(file_id)
            await bot.download_file(file.file_path, temp_path)

            self.logger.info(f"Фото сохранено во временный файл: {temp_path}")
            return temp_path

        except Exception as e:
            self.logger.error(f"Ошибка при скачивании фото: {str(e)}")
            return None

    def _get_error_message(self, error_code: ErrorCode) -> str:
        """
        Получает текстовое описание ошибки

        :param error_code: Код ошибки
        :return: Текстовое описание
        """
        error_messages = {
            ErrorCode.USER_ALREADY_EXISTS: "Игрок с таким именем и фамилией уже существует",
            ErrorCode.INVALID_INPUT: "Некорректные входные данные",
            ErrorCode.DATABASE_ERROR: "Ошибка базы данных",
            ErrorCode.USER_NOT_FOUND: "Игрок не найден",
        }
        return error_messages.get(error_code, "Неизвестная ошибка")

    async def players_list_callback(self, callback: CallbackQuery, state: FSMContext) -> None:
        """
        Обработчик кнопки списка игроков

        :param callback: Callback запрос от кнопки
        :param state: Состояние FSM
        """
        self.logger.info(f"Админ {callback.from_user.id} запросил список игроков")
        await state.clear()

        try:
            players = await self.players_handler.get_all_players()

            if not players:
                await AdminMessageSender().send_or_edit_message(
                    target=callback,
                    text=self.locale.bot.get("admin_no_players_found"),
                    reply_markup=self.keyboard.back_to_players_management_keyboard
                )
            else:
                players_text = self._format_players_list(players)
                await AdminMessageSender().send_or_edit_message(
                    target=callback,
                    text=players_text,
                    reply_markup=self.keyboard.back_to_players_management_keyboard
                )

        except Exception as e:
            self.logger.error(f"Ошибка при получении списка игроков: {str(e)}")
            await callback.message.answer(
                self.locale.bot.get("error_operation"),
                reply_markup=self.keyboard.back_to_players_management_keyboard
            )

        await callback.answer()

    def _format_players_list(self, players: list) -> str:
        """
        Форматирует список игроков для отображения

        :param players: Список игроков
        :return: Отформатированный текст
        """
        if not players:
            return self.locale.bot.get("admin_no_players_found")

        header = self.locale.ui.get("admin_players_list_header") + "\n\n"
        players_text = []

        for i, player in enumerate(players, 1):
            player_text = (
                f"{i}. {player.first_name} {player.last_name}\n"
                f"   🎮 Игр: {player.games_played} | "
                f"📊 Уровень: {player.player_level.value} ({player.numeric_level})\n"
            )
            players_text.append(player_text)

        return header + "\n".join(players_text)

    async def delete_players_callback(self, callback: CallbackQuery, state: FSMContext) -> None:
        """
        Обработчик кнопки удаления игроков

        :param callback: Callback запрос от кнопки
        :param state: Состояние FSM
        """
        self.logger.info(f"Админ {callback.from_user.id} открыл меню удаления игроков")
        await state.clear()

        try:
            players = await self.players_handler.get_all_players()

            if not players:
                await AdminMessageSender().send_or_edit_message(
                    target=callback,
                    text=self.locale.bot.get("admin_no_players_found"),
                    reply_markup=self.keyboard.back_to_players_management_keyboard
                )
            else:
                players_text = self._format_players_list_for_deletion(players)
                await AdminMessageSender().send_or_edit_message(
                    target=callback,
                    text=players_text,
                    reply_markup=self.keyboard.players_delete_keyboard(players)
                )

        except Exception as e:
            self.logger.error(f"Ошибка при получении списка игроков для удаления: {str(e)}")
            await callback.message.answer(
                self.locale.bot.get("error_operation"),
                reply_markup=self.keyboard.back_to_players_management_keyboard
            )

        await callback.answer()

    def _format_players_list_for_deletion(self, players: list) -> str:
        """
        Форматирует список игроков для удаления

        :param players: Список игроков
        :return: Отформатированный текст
        """
        if not players:
            return self.locale.ui.get("admin_no_players_found")

        header = self.locale.ui.get("admin_delete_players_header") + "\n\n"
        players_text = []

        for i, player in enumerate(players, 1):
            player_text = (
                f"{i}. {player.first_name} {player.last_name}\n"
                f"   🎮 Сыграно игр: {player.games_played}\n"
                f"   📊 Уровень: {player.player_level.value}\n"
                f"   🔢 Числовой уровень: {player.numeric_level}\n"
            )
            players_text.append(player_text)

        return header + "\n".join(players_text)

    async def delete_player_callback(self, callback: CallbackQuery, state: FSMContext) -> None:
        """
        Обработчик кнопки удаления конкретного игрока

        :param callback: Callback запрос от кнопки
        :param state: Состояние FSM
        """
        try:
            player_id = int(callback.data.replace("delete_player_", ""))
            self.logger.info(f"Админ {callback.from_user.id} запросил удаление игрока {player_id}")

            player = await self.players_handler.get_player(player_id)
            if not player:
                await callback.answer(self.locale.bot.get("admin_player_not_found"), show_alert=True)
                return

            # Показываем подтверждение удаления
            confirmation_text = self.locale.ui.get("admin_confirm_delete_player").format(
                first_name=player.first_name,
                last_name=player.last_name
            )

            await AdminMessageSender().send_or_edit_message(
                target=callback,
                text=confirmation_text,
                reply_markup=self.keyboard.confirm_delete_player_keyboard(player_id)
            )

        except Exception as e:
            self.logger.error(f"Ошибка при обработке удаления игрока: {str(e)}")
            await callback.answer(self.locale.bot.get("error_operation"), show_alert=True)

        await callback.answer()

    async def confirm_delete_player_callback(self, callback: CallbackQuery, state: FSMContext) -> None:
        """
        Обработчик подтверждения удаления игрока

        :param callback: Callback запрос от кнопки
        :param state: Состояние FSM
        """
        try:
            player_id = int(callback.data.replace("confirm_delete_player_", ""))
            self.logger.info(f"Админ {callback.from_user.id} подтвердил удаление игрока {player_id}")

            # Удаляем игрока
            result = await self.players_handler.delete_player(player_id)

            if result == ErrorCode.SUCCESSFUL:
                await AdminMessageSender().send_or_edit_message(
                    target=callback,
                    text=self.locale.ui.get("admin_player_delete_success"),
                    reply_markup=self.keyboard.back_to_players_management_keyboard
                )
                self.logger.info(f"Игрок {player_id} успешно удален")
            else:
                error_msg = self._get_error_message(result)
                await AdminMessageSender().send_or_edit_message(
                    target=callback,
                    text=self.locale.bot.get("admin_player_delete_error").format(error=error_msg),
                    reply_markup=self.keyboard.back_to_players_management_keyboard
                )
                self.logger.error(f"Ошибка удаления игрока {player_id}: {error_msg}")

        except Exception as e:
            self.logger.error(f"Ошибка при подтверждении удаления игрока: {str(e)}")
            await callback.answer(self.locale.bot.get("error_operation"), show_alert=True)

        await callback.answer()

    async def cancel_delete_player_callback(self, callback: CallbackQuery, state: FSMContext) -> None:
        """
        Обработчик отмены удаления игрока

        :param callback: Callback запрос от кнопки
        :param state: Состояние FSM
        """
        self.logger.info(f"Админ {callback.from_user.id} отменил удаление игрока")
        await self.delete_players_callback(callback, state)

    async def cancel_operation(self, callback: CallbackQuery, state: FSMContext) -> None:
        """
        Отмена операции и возврат в меню управления игроками

        :param callback: Callback запрос от кнопки
        :param state: Состояние FSM
        """
        self.logger.info(f"Админ {callback.from_user.id} отменил операцию")
        await state.clear()
        await self.manage_players_panel(callback, state)
