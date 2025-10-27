from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State


class AdminStates(StatesGroup):
    """
    Состояния для админских операций
    """
    waiting_for_user_input = State()
    waiting_for_username = State()
    waiting_for_role = State()
    waiting_for_delete_confirmation = State()
    waiting_for_player_name = State()  # Для имени игрока
    waiting_for_player_photo = State()  # Для фото игрока
    waiting_for_player_games = State()  # Для количества игр


class AdminStateManager:
    """
    Управление состояниями админ-панели
    """

    @staticmethod
    async def setup_add_user_flow(state: FSMContext) -> None:
        """
        Настройка состояния для добавления пользователя
        """
        await state.clear()
        await state.set_state(AdminStates.waiting_for_user_input)

    @staticmethod
    async def setup_role_selection(self, state: FSMContext, user_data: dict) -> None:
        """
        Настройка состояния для выбора роли
        """
        await state.update_data(**user_data)
        await state.set_state(AdminStates.waiting_for_role)

    @staticmethod
    async def setup_delete_confirmation(self, state: FSMContext, user_id: int) -> None:
        """
        Настройка состояния для подтверждения удаления
        """
        await state.update_data(delete_user_id=user_id)
        await state.set_state(AdminStates.waiting_for_delete_confirmation)
