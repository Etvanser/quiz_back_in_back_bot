from aiogram import Router

from logger import Logger


logger = Logger().get_logger()


class RoutersRecorder:
    """
    Фабрика для динамической регистрации маршрутов
    """
    _routers_factory = {}

    @classmethod
    def record_router(cls, router_class: type) -> type:
        """
        Декоратор для регистрации классов маршрутов

        :param router_class: Класс обработчика
        """
        logger.info(f"Регистрируем класс: {router_class.__name__}")
        cls._routers_factory[router_class.__name__] = router_class
        return router_class

    @classmethod
    def get_routers(cls) -> dict[str, type]:
        """
        Возвращает словарь зарегистрированных маршрутов
        """
        return cls._routers_factory

    @classmethod
    def create_all_routers(cls) ->list[Router]:
        """
        Создает все зарегистрированные роутеры
        """
        routers = []
        for name, router_class in cls._routers_factory.items():
            logger.info(f"🛠️ Создаем роутер: {name}")
            # Создаем новый экземпляр Router для каждого класса
            router_instance = Router()
            # Создаем обработчик, который регистрирует хендлеры в этом роутере
            router_class(router_instance)
            routers.append(router_instance)

        logger.info(f"✅ Создано {len(routers)} роутеров")
        return routers

    @classmethod
    def setup_main_router(cls) -> Router:
        """
        Создает главный роутер со всеми зарегистрированными роутерами
        """
        main_router = Router()
        for router in cls.create_all_routers():
            main_router.include_router(router)

        logger.info(f"✅ Создан главный роутер с {len(cls._routers_factory)} дочерними роутерами")
        return main_router
