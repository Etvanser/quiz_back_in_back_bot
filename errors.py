from enum import IntEnum


class ErrorCode(IntEnum):
    """
    Коды ошибок
    """
    SUCCESSFUL = 0
    INIT_DB_ERROR = 1          # Ошибка инициализации БД
    HANDLER_REGISTRATION_ERROR = 2    # Ошибка инициализации обработчиков событий
    ErrorInit = 3            # Ошибка инициализации(общая)
    FAILED_ERROR = 4         # Общая ошибка
    TOKEN_ERROR = 5          # Ошибка токена для бота
    ENGINE_INIT_ERROR = 6    # Ошибка инициализация движка
    PARTIAL_SUCCESS = 7      # Частичный успех
