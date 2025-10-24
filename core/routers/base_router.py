from abc import ABC, abstractmethod

from aiogram import Router

from locale import Locale


class BaseRouter(ABC):
    """
    Базовый класс для всех роутеров
    """

    def __init__(self, router: Router) -> None:
        self.locale = Locale()
        self.router = router
        self._register_handlers()


    @abstractmethod
    def _register_handlers(self) -> None:
        """
        Метод для регистрации обработчиков
        """
        raise NotImplementedError
