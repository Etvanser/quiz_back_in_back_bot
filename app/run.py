import asyncio

from core.engine import EngineBot
from core.routers import StartRouter


async def run():
    """
    Запуск бота
    """
    bot_engine = EngineBot()
    return await bot_engine.start()

if __name__ == "__main__":
    bot = EngineBot()
    asyncio.run(run())
