from telegram.error import TelegramError


class BotSendMessageError(TelegramError):
    """Ошибка при попытке отправить сообщение"""
    pass


class BotApiAnswerError(TelegramError):
    """Ошибка ответа API Бота Telegram."""
    pass
