from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from core.router_recorder import RoutersRecorder
from core.routers import BaseRouter



@RoutersRecorder.record_router
class StartRouter(BaseRouter):
    """
    Роутер для стартовых команд
    """

    def _register_handlers(self) -> None:
        self.router.message(CommandStart())(self.start_command)

    async def start_command(self, message: Message, state: FSMContext) -> None:
        await state.clear()
        await message.answer(
            "👋 Добро пожаловать!\n\n"
            "Этот бот поможет вам...\n"
            "Используйте /help для просмотра доступных команд"
        )
