import json
from pathlib import Path

from const import PathLike
from logger import Logger


logger = Logger().get_logger()


def load_config(config_file: PathLike) -> dict:
    """
    Загрузка данных из конфига

    :param config_file: Название конфиг файла через .json

    :return: Данные из конфига в виде словаря
    """
    config_path = Path(config_file)

    if config_path.is_file():
        with open(config_file) as file:
            data = json.load(file)
            logger.info(f"Конфиг {config_file} успешно прочитан")
            return data
    logger.error(f"Ошибка при загрузке конфига {config_file}")
    return {}
