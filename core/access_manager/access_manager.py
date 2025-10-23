from typing import Set, Dict
from abc import ABC, abstractmethod
from aiogram.fsm.storage.base import BaseStorage
from aiogram.fsm.context import FSMContext
from aiogram.types import User as TgUser

from core.config import Config


class BaseAccessManager(ABC):
    """Базовый класс для управления доступом"""

    @abstractmethod
    async def is_user_allowed(self, user_id: int) -> bool:
        """
        Проверяет, имеет ли пользователь доступ к боту
        """
        raise NotImplementedError

    @abstractmethod
    async def add_allowed_user(self, user_id: int, added_by: int) -> bool:
        """
        Добавляет пользователя в список разрешенных
        """
        raise NotImplementedError

    @abstractmethod
    async def is_admin(self, user_id: int) -> bool:
        """
        Проверяет, является ли пользователь администратором
        """
        raise NotImplementedError
