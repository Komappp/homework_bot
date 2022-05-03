import requests
import os
import time
from dotenv import load_dotenv
import telegram
import logging
import sys
from http import HTTPStatus

load_dotenv()

logger = logging.getLogger(__name__)
# не уверен что правильно что я его вынес
# но иначе не проходит тест

PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

RETRY_TIME = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}
ERRORS = []
TIME_PERIOD_IN_SECONDS = 2592000

HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


def send_message(bot, message):
    """отправляет сообщения в телеграм."""
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logger.info('Отправлено сообщение в телеграм')
    except Exception:
        raise Exception('Не удалось отправить сообщение')


def get_api_answer(current_timestamp):
    """Делает запрос к API и возвращает данные преобразованные из JSON."""
    logger.info('Начался запрос к API')
    timestamp = current_timestamp or int(time.time())
    params = {'from_date': timestamp}
    try:
        homework_statuses = requests.get(
            ENDPOINT, headers=HEADERS, params=params
        )
    except Exception as err:
        raise ConnectionError('Нет ответа от API') from err
    if not homework_statuses.status_code == HTTPStatus.OK:
        raise Exception('Неудачный ответ от сервера API')
    return homework_statuses.json()


def check_response(response):
    """Проверяет ответ от API и извлекает список с домашками."""
    logger.info('Началась проверка ответа от сервера API')
    if not isinstance(response, dict):
        raise TypeError('Ответ не является словарём')
    if 'current_date' not in response or 'homeworks' not in response:
        raise KeyError('Отсутствует ключ "current_date" или "homeworks"')
    if not isinstance(response['homeworks'], list):
        raise TypeError('Ключ "homeworks" не список')
    homeworks = response['homeworks']
    return homeworks


def parse_status(homework):
    """Извлекает имя и статус домашки."""
    #  !С ЭТОЙ ПРОВЕРКОЙ НЕ ПРОХОДИТ ТЕСТ!
    if 'status' not in homework or 'homework_name' not in homework:
        raise KeyError('Нужные ключи в ответе API отсутствуют')
    homework_name = homework['homework_name']
    homework_status = homework['status']
    if homework_status not in HOMEWORK_VERDICTS:
        raise Exception('Неизвестный статус домашки')
    verdict = HOMEWORK_VERDICTS[homework_status]
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def check_tokens():
    """Проверка доступности переменных окружения."""
    if all([PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID]):
        return True
    else:
        return False


def main():
    """Основная логика работы бота."""
    if not check_tokens():
        logger.critical(
            'Отсутствуют необходимые для работы переменные окружения'
        )
        sys.exit()
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time())
    status_message = None
    while True:
        try:
            response = get_api_answer(
                current_timestamp - TIME_PERIOD_IN_SECONDS
            )
            homeworks = check_response(response)
            if not homeworks:
                logger.info('Домашние работы отсутсвуют')
            homework = homeworks[0]
            message = parse_status(homework)
            if message != status_message:
                send_message(bot, message)
                status_message = message
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            logger.error(message)
            if message not in ERRORS:
                send_message(bot, message)
                ERRORS.append(message)
        else:
            logger.info('Совершена проверка статуса домашки')
        finally:
            time.sleep(RETRY_TIME)
            current_timestamp = int(time.time())


if __name__ == '__main__':
    logger.setLevel(logging.INFO)
    handler = logging.StreamHandler(stream=sys.stdout)
    logger.addHandler(handler)
    formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(message)s - '
        'функция %(funcName)s - строка %(lineno)d'
    )
    handler.setFormatter(formatter)
    main()
