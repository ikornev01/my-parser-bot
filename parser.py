import requests
from bs4 import BeautifulSoup
import schedule
import time
import os
import logging
from telegram import Bot, Update
from telegram.ext import CommandHandler, Updater, CallbackContext
from datetime import datetime, timedelta

# Ваш Telegram токен
TELEGRAM_TOKEN = '7938305973:AAE4YpvTZ-9VWSgVNmUdzTxv-yWMsa2-aC4'

# Инициализация бота
bot = Bot(token=TELEGRAM_TOKEN)

# Путь к файлу для сохранения подписчиков
SUBSCRIBERS_FILE = 'subscribers.txt'

# Настраиваем логирование
logging.basicConfig(
    filename='parser.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# URL страницы для парсинга
url = 'https://crvenazvezda.iticket.rs/en.html'

# Хранение времени последнего запроса
last_request_time = None
barcelona_found = False

# Загружаем подписчиков из резервного файла при запуске
def load_subscribers():
    if os.path.exists(SUBSCRIBERS_FILE):
        with open(SUBSCRIBERS_FILE, 'r') as f:
            return set(f.read().splitlines())
    return set()

# Сохраняем подписчиков в файл
def save_subscribers():
    with open(SUBSCRIBERS_FILE, 'w') as f:
        f.write('\n'.join(subscribers))

# Инициализация списка подписчиков
subscribers = load_subscribers()

# Функция для получения HTML-страницы
def get_html_page(url):
    global last_request_time
    try:
        response = requests.get(url)
        if response.status_code == 200:
            logging.info("Успешно получена страница")
            # Добавляем 2 часа к текущему времени
            last_request_time = (datetime.now() + timedelta(hours=2)).strftime('%H:%M')  # Сохраняем в формате чч:мм
            return response.text
        else:
            logging.error(f"Ошибка при запросе страницы: {response.status_code}")
            return None
    except Exception as e:
        logging.error(f"Ошибка запроса: {e}")
        return None

# Функция для поиска слова на странице
def check_for_word(soup, word):
    page_text = soup.get_text()
    if word.lower() in page_text.lower():
        logging.info(f"Найдено упоминание: {word}")
        return True
    else:
        logging.info(f"Упоминание {word} не найдено")
        return False

# Функция для сохранения состояния
def save_state(filename, state):
    with open(filename, 'w') as f:
        f.write(state)

# Функция для загрузки состояния
def load_state(filename):
    if os.path.exists(filename):
        with open(filename, 'r') as f:
            return f.read()
    return None

# Функция для отправки уведомлений всем подписчикам
def send_telegram_message(message):
    try:
        for subscriber in subscribers:
            bot.send_message(chat_id=subscriber, text=message)
        logging.info("Уведомление отправлено в Telegram всем подписчикам")
    except Exception as e:
        logging.error(f"Ошибка отправки уведомления в Telegram: {e}")

# Функция для отправки сообщения всем подписчикам о необходимости повторной подписки
def notify_all_subscribers():
    message = "Бот был обновлен. Пожалуйста, отправьте команду /start, чтобы подписаться на ежедневные уведомления."
    send_telegram_message(message)

# Основная логика парсера
def job():
    global barcelona_found
    logging.info("Запуск парсера")
    html = get_html_page(url)
    if html:
        soup = BeautifulSoup(html, 'html.parser')
        state_file = "barcelona_state.txt"
        current_state = load_state(state_file)
        if check_for_word(soup, "Barcelona") and current_state != "found":
            barcelona_found = True
            # Отправляем сообщение с временем последнего запроса с учетом +2 часа
            message = f"Найдено упоминание 'Barcelona' на сайте билетов Црвена Звезда! Время последнего запроса (+2 часа): {last_request_time}"
            send_telegram_message(message)
            save_state(state_file, "found")
        else:
            barcelona_found = False
            logging.info("Состояние не изменилось или упоминание уже было найдено.")

# Ежедневное уведомление о статусе
def daily_status_notification():
    state_file = "barcelona_state.txt"
    current_state = load_state(state_file)
    if current_state == "found":
        send_telegram_message(f"Ежедневное уведомление: Билеты на матч с 'Barcelona' уже доступны. Время последнего запроса (+2 часа): {last_request_time}")
    else:
        send_telegram_message(f"Ежедневное уведомление: Билеты на матч с 'Barcelona' еще не появились. Время последнего запроса (+2 часа): {last_request_time}")

# Команда для запроса последнего состояния
def last_request(update: Update, context: CallbackContext):
    global last_request_time, barcelona_found
    if last_request_time:
        if barcelona_found:
            update.message.reply_text(f"Найдено слово 'Barcelona'. Время последнего запроса (+2 часа): {last_request_time}")
        else:
            update.message.reply_text(f"Слово 'Barcelona' не найдено. Время последнего запроса (+2 часа): {last_request_time}")
    else:
        update.message.reply_text("Запросов еще не было.")

# Команда для подписки на уведомления и приветственное сообщение
def start(update: Update, context: CallbackContext):
    user_id = str(update.message.chat_id)
    if user_id not in subscribers:
        subscribers.add(user_id)
        save_subscribers()  # Сохраняем подписчиков каждый раз, когда добавляется новый
        update.message.reply_text("Вы подписались на уведомления о доступности билетов.")
    else:
        update.message.reply_text("Вы уже подписаны на уведомления.")
    update.message.reply_text("Добро пожаловать! Я буду уведомлять вас о доступности билетов на матч с 'Barcelona'.")

# Настройка регулярных проверок
schedule.every(2).minutes.do(job)  # Проверка на "Barcelona" каждые 2 минуты
schedule.every().day.at("09:00").do(daily_status_notification)  # Ежедневное уведомление в 09:00

# Функция для инициализации бота
def main():
    updater = Updater(token=TELEGRAM_TOKEN, use_context=True)
    dispatcher = updater.dispatcher

    # Команды
    dispatcher.add_handler(CommandHandler("start", start))
    dispatcher.add_handler(CommandHandler("last_request", last_request))

    # Запуск бота
    updater.start_polling()

    # После перезапуска бота отправляем сообщение всем подписчикам
    notify_all_subscribers()

    # Запуск цикла для schedule
    while True:
        schedule.run_pending()
        time.sleep(1)

if __name__ == "__main__":
    main()

