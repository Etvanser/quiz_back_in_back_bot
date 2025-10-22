from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

from core.config import Config
from core.router_recorder.router_recorder import RoutersRecorder


class EngineBot:
    """
    Движок бота
    """

    def __init__(self) -> None:
        """
        Создает экземпляр EngineBot
        """
        self._bot = Bot(token=Config().data.token)
        self._dp = Dispatcher(storage=MemoryStorage())
        self._dp.include_router(RoutersRecorder.setup_main_router())

    async def start(self) -> None:
        """
        Запуск бота
        """
        await self._dp.start_polling(self._bot)
