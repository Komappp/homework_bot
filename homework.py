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

RETRY_TIME = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}
ERRORS = []

HOMEWORK_STATUSES = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


def generate_exception(message):
    """Делает запись в лог и генерит исключение."""
    logger.error(message)
    raise Exception(message)


def send_message(bot, message):
    """отправляет сообщения в телеграм."""
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logger.info('Отправлено сообщение в телеграм')
    except Exception:
        logger.error('Не удалось отправить сообщение')


def get_api_answer(current_timestamp):
    """Делает запрос к API и возвращает данные преобразованные из JSON."""
    timestamp = current_timestamp or int(time.time())
    params = {'from_date': timestamp}
    homework_statuses = requests.get(ENDPOINT, headers=HEADERS, params=params)
    if not homework_statuses.status_code == 200:
        message = 'Ответ от API не получен'
        generate_exception(message)
    return homework_statuses.json()


def check_response(response):
    """Проверяет ответ от API и извлекает список с домашками."""
    if not isinstance(response['homeworks'], list):
        message = 'homeworks не список'
        generate_exception(message)
    homeworks = response['homeworks']
    return homeworks


def parse_status(homework):
    """Извлекает имя и статус домашки."""
    homework_name = homework['homework_name']
    if 'status' not in homework:
        message = 'Нужные ключи в ответе API отсутствуют'
        generate_exception(message)
    homework_status = homework['status']
    verdict = HOMEWORK_STATUSES[homework_status]
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def check_tokens():
    """Проверка доступности переменных окружения."""
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
            homeworks = check_response(response)
            if len(homeworks) < 1:
                message = 'Пустой словарь'
                generate_exception(message)
            homework = homeworks[0]
            message = parse_status(homework)
            if message and (message != status_message):
                send_message(bot, message)
                status_message = message
            time.sleep(RETRY_TIME)
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            logger.error(message)
            if message not in ERRORS:
                send_message(bot, message)
                ERRORS.append(message)
            time.sleep(RETRY_TIME)
        else:
            logger.info('Совершена проверка')


if __name__ == '__main__':
    main()
