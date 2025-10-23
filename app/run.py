import asyncio

from app import Application
from core.routers import StartRouter
from errors import ErrorCode


async def run():
    """
    Запуск бота
    """
    app = Application()

    if await app.run() != ErrorCode.SUCCESSFUL:
        print("Бот не запустился")

if __name__ == "__main__":
    asyncio.run(run())
