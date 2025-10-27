from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Optional
import uuid

from const import PHOTOS_DIR
from core.database_manager.base_database_handler import BaseDatabaseHandler
from core.database_manager.const_bd import TableBD
from errors import ErrorCode
from logger import Logger


logger = Logger().get_logger()


class PlayerLevel(str, Enum):
    """
    Текстовые уровни игроков
    """
    BEGINNER = "Новичок"
    INTERMEDIATE = "Любитель"
    ADVANCED = "Профессионал"
    EXPERT = "Эксперт"


@dataclass
class QuizPlayer:
    """
    Данные игрока квиза
    """
    player_id: int
    first_name: str
    last_name: str
    photo: Optional[str] = None
    games_played: int = 0
    player_level: PlayerLevel = PlayerLevel.BEGINNER
    numeric_level: int = 1


class DatabaseQuizPlayerHandler(BaseDatabaseHandler):
    """
    Обработчик для работы с игроками квиза
    """

    def __init__(self) -> None:
        """
        Создает экземпляр DatabaseQuizPlayerHandler
        """
        super().__init__()
        self._table_name = TableBD.QUIZ_PLAYERS.value
        PHOTOS_DIR.mkdir(parents=True, exist_ok=True)
        self.allowed_extensions = {'.jpg', '.jpeg', '.png'}

    async def add_player(
            self,
            first_name: str,
            last_name: str,
            photo_path: Optional[str] = None,
            games_played: int = 0,
            player_level: PlayerLevel = PlayerLevel.BEGINNER,
            numeric_level: int = 0
    ) -> ErrorCode:
        """
        Добавление нового игрока квиза

        :param first_name: Имя игрока
        :param last_name: Фамилия игрока
        :param photo_path: Путь к файлу фото игрока (опционально)
        :param games_played: Количество сыгранных игр
        :param player_level: Текстовый уровень игрока
        :param numeric_level: Цифровой уровень игрока (1-100)

        :return: Код результата операции
        """
        try:
            if numeric_level < 0:
                logger.warning(f"Некорректный цифровой уровень: {numeric_level}")
                return ErrorCode.INVALID_INPUT

            existing_player = await self._execute(
                f"SELECT player_id FROM {self._table_name} WHERE first_name = ? AND last_name = ?",
                (first_name, last_name),
                fetch=True
            )
            if existing_player:
                logger.warning(f"Игрок {first_name} {last_name} уже существует")
                return ErrorCode.USER_ALREADY_EXISTS

            # Обрабатываем фото если оно есть
            final_photo_path = None
            if photo_path:
                final_photo_path = await self._process_photo(photo_path, first_name, last_name)
                if not final_photo_path:
                    logger.warning(f"Не удалось обработать фото для игрока {first_name} {last_name}")

            # Добавляем нового игрока
            await self._execute(
                f"""
                        INSERT INTO {self._table_name} 
                        (first_name, last_name, photo, games_played, player_level, numeric_level)
                        VALUES (?, ?, ?, ?, ?, ?)
                        """,
                (first_name, last_name, final_photo_path, games_played, player_level.value, numeric_level)
            )

            logger.info(f"Игрок {first_name} {last_name} успешно добавлен")
            return ErrorCode.SUCCESSFUL

        except Exception as e:
            logger.error(f"Ошибка при добавлении игрока: {e}")
            return ErrorCode.DATABASE_ERROR

    async def _process_photo(self, photo_path: str, first_name: str, last_name: str) -> Optional[str]:
        """
        Обрабатывает и сохраняет фото игрока

        :param photo_path: Путь к исходному файлу фото
        :param first_name: Имя игрока
        :param last_name: Фамилия игрока
        :return: Путь к сохраненному файлу или None в случае ошибки
        """
        try:
            source_path = Path(photo_path)

            # Проверяем существование файла
            if not source_path.exists():
                logger.error(f"Файл фото не найден: {photo_path}")
                return None

            # Проверяем расширение файла
            if source_path.suffix.lower() not in self.allowed_extensions:
                logger.error(f"Неподдерживаемый формат фото: {source_path.suffix}")
                return None

            # Генерируем уникальное имя файла
            safe_first_name = "".join(c for c in first_name if c.isalnum() or c in (' ', '-', '_')).rstrip()
            safe_last_name = "".join(c for c in last_name if c.isalnum() or c in (' ', '-', '_')).rstrip()
            unique_id = uuid.uuid4().hex[:8]
            new_filename = f"{safe_first_name}_{safe_last_name}_{unique_id}{source_path.suffix.lower()}"
            new_filepath = PHOTOS_DIR / new_filename

            # Копируем файл
            import shutil
            shutil.copy2(source_path, new_filepath)

            logger.info(f"Фото сохранено: {new_filepath}")
            return str(new_filepath)

        except Exception as e:
            logger.error(f"Ошибка при обработке фото: {e}")
            return None

    async def update_player_photo(self, player_id: int, photo_path: str) -> ErrorCode:
        """
        Обновляет фото игрока

        :param player_id: ID игрока
        :param photo_path: Путь к новому файлу фото
        :return: Код результата операции
        """
        try:
            player = await self.get_player(player_id)
            if not player:
                return ErrorCode.USER_NOT_FOUND

            # Удаляем старое фото если оно есть
            if player.photo:
                await self._delete_photo_file(player.photo)

            # Обрабатываем новое фото
            new_photo_path = await self._process_photo(photo_path, player.first_name, player.last_name)
            if not new_photo_path:
                return ErrorCode.INVALID_INPUT

            # Обновляем путь к фото в БД
            return await self.update_player(player_id, photo=new_photo_path)

        except Exception as e:
            logger.error(f"Ошибка при обновлении фото игрока {player_id}: {e}")
            return ErrorCode.DATABASE_ERROR

    async def _delete_photo_file(self, photo_path: str) -> bool:
        """
        Удаляет файл фото

        :param photo_path: Путь к файлу фото
        :return: True если удалено успешно, False в случае ошибки
        """
        try:
            photo_file = Path(photo_path)
            if photo_file.exists():
                photo_file.unlink()
                logger.info(f"Фото удалено: {photo_path}")
                return True
            return False
        except Exception as e:
            logger.error(f"Ошибка при удалении фото {photo_path}: {e}")
            return False

    async def delete_player(self, player_id: int) -> ErrorCode:
        """
        Удаление игрока

        :param player_id: ID игрока
        :return: Код результата операции
        """
        try:
            # Получаем данные игрока для удаления фото
            player = await self.get_player(player_id)
            if player and player.photo:
                await self._delete_photo_file(player.photo)

            await self._execute(
                f"DELETE FROM {self._table_name} WHERE player_id = ?",
                (player_id,)
            )

            logger.info(f"Игрок {player_id} успешно удален")
            return ErrorCode.SUCCESSFUL

        except Exception as e:
            logger.error(f"Ошибка при удалении игрока {player_id}: {e}")
            return ErrorCode.DATABASE_ERROR

    async def get_player_photo(self, player_id: int) -> Optional[str]:
        """
        Получает путь к фото игрока

        :param player_id: ID игрока
        :return: Путь к файлу фото или None если фото нет
        """
        try:
            player = await self.get_player(player_id)
            return player.photo if player else None
        except Exception as e:
            logger.error(f"Ошибка при получении фото игрока {player_id}: {e}")
            return None

    async def validate_photo_file(self, file_path: str) -> bool:
        """
        Проверяет валидность файла фото

        :param file_path: Путь к файлу
        :return: True если файл валиден, False в противном случае
        """
        try:
            path = Path(file_path)

            # Проверяем существование
            if not path.exists():
                logger.error(f"Файл не существует: {file_path}")
                return False

            # Проверяем расширение
            if path.suffix.lower() not in self.allowed_extensions:
                logger.error(f"Неподдерживаемый формат: {path.suffix}")
                return False

            # Проверяем размер файла (максимум 10MB)
            max_size = 10 * 1024 * 1024  # 10MB
            if path.stat().st_size > max_size:
                logger.error(f"Файл слишком большой: {path.stat().st_size} байт")
                return False

            return True

        except Exception as e:
            logger.error(f"Ошибка при проверке файла {file_path}: {e}")
            return False

    async def get_player(self, player_id: int) -> Optional[QuizPlayer]:
        """
        Получение игрока по ID

        :param player_id: ID игрока
        :return: Объект игрока или None если не найден
        """
        try:
            result = await self._execute(
                f"SELECT * FROM {self._table_name} WHERE player_id = ?",
                (player_id,),
                fetch=True
            )

            if not result:
                return None

            player_data = result[0]
            return QuizPlayer(
                player_id=player_data['player_id'],
                first_name=player_data['first_name'],
                last_name=player_data['last_name'],
                photo=player_data['photo'],
                games_played=player_data['games_played'],
                player_level=PlayerLevel(player_data['player_level']),
                numeric_level=player_data['numeric_level']
            )

        except Exception as e:
            logger.error(f"Ошибка при получении игрока {player_id}: {e}")
            return None

    async def get_all_players(self) -> list[QuizPlayer]:
        """
        Получение всех игроков

        :return: Список всех игроков
        """
        try:
            result = await self._execute(
                f"SELECT * FROM {self._table_name} ORDER BY numeric_level DESC, last_name, first_name",
                fetch=True
            )

            players = []
            for player_data in result:
                players.append(QuizPlayer(
                    player_id=player_data['player_id'],
                    first_name=player_data['first_name'],
                    last_name=player_data['last_name'],
                    photo=player_data['photo'],
                    games_played=player_data['games_played'],
                    player_level=PlayerLevel(player_data['player_level']),
                    numeric_level=player_data['numeric_level']
                ))

            return players

        except Exception as e:
            logger.error(f"Ошибка при получении списка игроков: {e}")
            return []

    async def update_player(
            self,
            player_id: int,
            first_name: Optional[str] = None,
            last_name: Optional[str] = None,
            photo: Optional[str] = None,
            games_played: Optional[int] = None,
            player_level: Optional[PlayerLevel] = None,
            numeric_level: Optional[int] = None
    ) -> ErrorCode:
        """
        Обновление данных игрока

        :param player_id: ID игрока
        :param first_name: Новое имя (опционально)
        :param last_name: Новая фамилия (опционально)
        :param photo: Новое фото (опционально)
        :param games_played: Новое количество игр (опционально)
        :param player_level: Новый текстовый уровень (опционально)
        :param numeric_level: Новый цифровой уровень (опционально)

        :return: Код результата операции
        """
        try:
            if numeric_level is not None and numeric_level < 0:
                logger.warning(f"Некорректный цифровой уровень: {numeric_level}")
                return ErrorCode.INVALID_INPUT

            update_fields = []
            params = []

            if first_name is not None:
                update_fields.append("first_name = ?")
                params.append(first_name)
            if last_name is not None:
                update_fields.append("last_name = ?")
                params.append(last_name)
            if photo is not None:
                update_fields.append("photo = ?")
                params.append(photo)
            if games_played is not None:
                update_fields.append("games_played = ?")
                params.append(games_played)
            if player_level is not None:
                update_fields.append("player_level = ?")
                params.append(player_level.value)
            if numeric_level is not None:
                update_fields.append("numeric_level = ?")
                params.append(numeric_level)

            if not update_fields:
                return ErrorCode.SUCCESSFUL

            params.append(player_id)

            await self._execute(
                f"UPDATE {self._table_name} SET {', '.join(update_fields)} WHERE player_id = ?",
                tuple(params)
            )

            logger.info(f"Данные игрока {player_id} успешно обновлены")
            return ErrorCode.SUCCESSFUL

        except Exception as e:
            logger.error(f"Ошибка при обновлении игрока {player_id}: {e}")
            return ErrorCode.DATABASE_ERROR

    async def update_numeric_level(self, player_id: int, numeric_level: int) -> ErrorCode:
        """
        Обновление только цифрового уровня игрока

        :param player_id: ID игрока
        :param numeric_level: Новый цифровой уровень
        :return: Код результата операции
        """
        return await self.update_player(player_id, numeric_level=numeric_level)

    async def update_text_level(self, player_id: int, player_level: PlayerLevel) -> ErrorCode:
        """
        Обновление только текстового уровня игрока

        :param player_id: ID игрока
        :param player_level: Новый текстовый уровень
        :return: Код результата операции
        """
        return await self.update_player(player_id, player_level=player_level)

    async def calculate_numeric_level_from_games(self, games_played: int) -> int:
        """
        Рассчитывает цифровой уровень на основе количества сыгранных игр

        :param games_played: Количество сыгранных игр
        :return: Цифровой уровень (без ограничения)
        """
        return games_played // 5

    async def calculate_text_level_from_games(self, games_played: int) -> PlayerLevel:
        """
        Рассчитывает текстовый уровень на основе количества сыгранных игр

        :param games_played: Количество сыгранных игр
        :return: Текстовый уровень игрока
        """
        # Каждые 25 игр повышают текстовый уровень
        level_tier = games_played // 25

        if level_tier >= 3:  # 75+ игр
            return PlayerLevel.EXPERT
        elif level_tier == 2:  # 50-74 игр
            return PlayerLevel.ADVANCED
        elif level_tier == 1:  # 25-49 игр
            return PlayerLevel.INTERMEDIATE
        else:  # 0-24 игр
            return PlayerLevel.BEGINNER

    async def auto_update_levels(self, player_id: int) -> ErrorCode:
        """
        Автоматическое обновление уровней игрока на основе статистики

        :param player_id: ID игрока
        :return: Код результата операции
        """
        try:
            player = await self.get_player(player_id)
            if not player:
                return ErrorCode.USER_NOT_FOUND

            new_numeric_level = await self.calculate_numeric_level_from_games(player.games_played)
            new_text_level = await self.calculate_text_level_from_games(player.games_played)

            # Обновляем уровни
            return await self.update_player(
                player_id,
                player_level=new_text_level,
                numeric_level=new_numeric_level
            )

        except Exception as e:
            logger.error(f"Ошибка при автоматическом обновлении уровней игрока {player_id}: {e}")
            return ErrorCode.DATABASE_ERROR

    async def increment_games_played(self, player_id: int) -> ErrorCode:
        """
        Увеличивает счетчик сыгранных игр и автоматически обновляет уровни

        :param player_id: ID игрока
        :return: Код результата операции
        """
        try:
            await self._execute(
                f"UPDATE {self._table_name} SET games_played = games_played + 1 WHERE player_id = ?",
                (player_id,)
            )

            await self.auto_update_levels(player_id)

            return ErrorCode.SUCCESSFUL
        except Exception as e:
            logger.error(f"Ошибка при увеличении счетчика игр для {player_id}: {e}")
            return ErrorCode.DATABASE_ERROR
