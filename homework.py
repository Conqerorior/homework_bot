import os
import sys

import requests
import logging
import time
import telegram

from http import HTTPStatus
from dotenv import load_dotenv, find_dotenv

from exceptions import BotSendMessageError, BotApiAnswerError

load_dotenv(find_dotenv())

PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

RETRY_PERIOD = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


def check_tokens():
    """Функция проверяет валидность токенов."""
    list_token = (PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID)

    if not all(list_token):
        logging.critical('Проверьте переменные окружения')
        raise Exception('Отсутствуют переменные окружения')


def send_message(bot, message):
    """Функция отправляет сообщение в Telegram."""
    logger = logging.getLogger(__name__)

    try:
        logger.debug('Подготовка к отправке сообщения')
        bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)
    except BotSendMessageError as e:
        raise telegram.error.TelegramError(f'Ошибка отправки сообщения {e}')
    else:
        logger.debug('Сообщение отправлено')


def get_api_answer(timestamp):
    """Функция проверяет API ответ."""
    logger = logging.getLogger(__name__)

    try:
        logger.debug(f'Запрос к API: {ENDPOINT}')
        response = requests.get(ENDPOINT,
                                headers=HEADERS,
                                params={'from_date': timestamp})

        if response.status_code != HTTPStatus.OK:
            logger.error(f'Недоступность ENDPOINT: {ENDPOINT}')
            raise BotApiAnswerError(f'Статус код: {response.status_code}')
        return response.json()
    except requests.RequestException as e:
        raise BotApiAnswerError(f'Сбой подключения {e}')


def check_response(response):
    """Функция проверяет корректность формы последней домашней работы."""
    logger = logging.getLogger(__name__)

    try:
        return response['homeworks'][0]
    except TypeError:
        errors = 'Результат не соответствует типу данных'
        logger.error(f'{errors}')
    except KeyError:
        errors = 'Ключ [homeworks] отсутствует'
        logger.error(f'{errors}')
    except IndexError:
        errors = 'Список пуст'
        logger.error(f'{errors}')
    raise TypeError('Ошибка возврата формы')


def parse_status(homework):
    """Достаем статус и вердикт домашней работы."""
    logger = logging.getLogger(__name__)

    try:
        logger.debug('Ожидаем статус и вердикт')
        status = homework['status']
        homework_name = homework['homework_name']
        verdict = HOMEWORK_VERDICTS[status]
    except KeyError:
        logger.error('Ключа не существует')
        raise Exception('Ключей [status] или [homework_name] нет!')

    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def main():
    """Основная логика работы бота."""
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.DEBUG)
    stream_handler = logging.StreamHandler(sys.stdout)
    format_logger = '%(asctime)s %(levelname)s %(message)s'
    formatter = logging.Formatter(format_logger)
    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)

    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    timestamp = 0
    last_message = None

    check_tokens()

    while True:
        try:
            response = get_api_answer(timestamp)
            homework = check_response(response)
            response_message = parse_status(homework)
            if response_message != last_message:
                send_message(bot, response_message)
            else:
                logger.debug('Статус проверки не изменился')

        except BotApiAnswerError as e:
            message = f'Сбой в работе программы: {e}'
            logger.error(message)
            send_message(bot, message)

        except BotSendMessageError as e:
            message = f'Сбой в работе программы: {e}'
            logger.error(message)

        except Exception as e:
            message = f'Сбой в работе программы: {e}'
            logger.error(message)
            send_message(bot, message)

        finally:
            time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    main()
