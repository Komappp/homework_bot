import requests
import os
import time
from dotenv import load_dotenv
import telegram
import datetime
import logging
import sys

load_dotenv()

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
handler = logging.StreamHandler(stream=sys.stdout)
logger.addHandler(handler)
formatter = logging.Formatter(
    '%(asctime)s - %(levelname)s - %(message)s'
)
handler.setFormatter(formatter)

PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

RETRY_TIME = 5
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuse/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}
ERRORS = []

HOMEWORK_STATUSES = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


def send_message(bot, message):
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logger.info('Отправлено сообщение в телеграм')
    except Exception:
        logger.error('Не удалось отправить сообщение')


def send_error_message(bot, message):
    if message not in ERRORS:
        send_message(bot, message)
        ERRORS.append(message)


def get_api_answer(current_timestamp):
    timestamp = current_timestamp or int(time.time())
    params = {'from_date': timestamp}
    homework_statuses = requests.get(ENDPOINT, headers=HEADERS, params=params)
    if not homework_statuses.status_code == 200:
        message = 'Ответ от API не получен'
        logger.error(message)
        raise Exception
    return homework_statuses.json()


def check_response(response):
    if not isinstance(response['homeworks'], list):
        logger.error('homeworks не список')
        raise Exception
    homeworks = response['homeworks']
    return homeworks


def parse_status(homework):
    homework_name = homework['homework_name']
    try:
        homework_status = homework['status']
    except Exception:
        logger.error('Нужные ключи в ответе API отсутствуют')
        raise Exception
    verdict = HOMEWORK_STATUSES[homework_status]
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def check_tokens():
    """Проверка доступности переменных окружения"""
    if PRACTICUM_TOKEN and TELEGRAM_TOKEN and TELEGRAM_CHAT_ID:
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
    from_date = datetime.datetime.now(tz=None) - datetime.timedelta(days=30)
    current_timestamp = time.mktime(from_date.timetuple())
    status_message = None
    while True:
        try:
            response = get_api_answer(int(current_timestamp))
            print(response)
            homeworks = check_response(response)
            if len(homeworks) < 1:
                raise Exception
            homework = homeworks[0]
            message = parse_status(homework)
            if message and (message != status_message):
                send_message(bot, message)
                status_message = message
            time.sleep(RETRY_TIME)
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            logger.error(message)
            if not message in ERRORS:
                send_error_message(bot, message)
                ERRORS.append(message)
            time.sleep(RETRY_TIME)
        else:
            logger.info('Совершена проверка')


if __name__ == '__main__':
    main()
