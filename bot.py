import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, Bot
import telegram
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
import asyncio
from random import uniform, choice
import os
import json
import requests
from apscheduler.schedulers.asyncio import AsyncIOScheduler

# Включаем логирование
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(level)s - %(message)s',
    level=logging.DEBUG  # Изменено с INFO на DEBUG для более детализированного логирования
)
logger = logging.getLogger(__name__)

# Список валютных пар
currency_pairs = [
    'GOLD', 'LATAM', 'IMX', 'BIN IDX', 'USD/CHF', 'GBP/JPY', 'PMX', 'EUR/CAD',
    'EUR/JPY', 'GBP/USD', 'EUR/GBP', 'NZD/JPY', 'EUR/USD', 'USD/JPY', 'ASIA',
    'INTEL', 'ALIBABA', 'AMAZON', 'APPLE', 'MASTERCARD', 'MICROSOFT', 'TESLA',
    'VISA', 'USD/CAD', 'AUD/JPY', 'NETFLIX', 'USD/CNH', 'FACEBOOK', 'GOOGLE',
    'AUD/NZD', 'CRYPTO IDX', 'AUD/CHF', 'DOWJONES30', 'NASDAQ', 'BITCOIN',
    'EUR/NZD', 'AUD/CAD', 'AUD/USD', 'CAD/CHF', 'CAD/JPY', 'CHF/JPY',
    'ETHEREUM', 'EUR/AUD', 'EUR/CHF', 'EUR/SEK', 'GBP/AUD', 'GBP/CAD',
    'GBP/CHF', 'GBP/NZD', 'GSMI', 'LITECOIN', 'MCDONALDS', 'NVIDIA', 'NZD/CAD',
    'NZD/CHF', 'NZD/USD', 'RIPPLE', 'SILVER', 'TOYOTA', 'USD/MXN', 'USD/NOK',
    'USD/SEK', 'USD/SGD', 'USD/ZAR'
]

# Пример словаря с URL-адресами картинок для каждой валютной пары
image_url = 'https://avatars.dzeninfra.ru/get-zen_doc/3530293/pub_6508970c6908147fa5ca2ee4_6508979174d98d3357fcab1b/scale_1200'
currency_images = {pair: image_url for pair in currency_pairs}

# Функция для генерации случайного курса и направления
def generate_exchange_rate():
    rate = round(uniform(0.5, 2.0), 4)
    direction = choice(['вверх📈', 'вниз📉'])
    return rate, direction

# Функция для получения реального курса валют
def get_real_exchange_rate(currency_pair):
    try:
        url = f"https://api.exchangerate-api.com/v4/latest/{currency_pair.split('/')[0]}"
        response = requests.get(url)
        data = response.json()
        return data['rates'].get(currency_pair.split('/')[1], 'Нет данных')
    except Exception as e:
        logger.error(f"Ошибка при получении реального курса для {currency_pair}: {e}")
        return 'Нет данных'

# Функция для сохранения данных пользователя в JSON файл
def save_user_data(user_id, data):
    file_path = 'user_data.json'
    if os.path.exists(file_path):
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read().strip()
                if content:
                    user_data = json.loads(content)
                else:
                    user_data = {}
        except (json.JSONDecodeError, FileNotFoundError) as e:
            logger.error(f"Ошибка при чтении файла user_data.json: {e}")
            user_data = {}
    else:
        user_data = {}

    user_data[user_id] = data

    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(user_data, f, ensure_ascii=False, indent=4)

# Команда /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.message.chat_id

    # Сохраняем данные пользователя
    user_data = {
        'chat_id': chat_id,
        'username': update.message.from_user.username,
        'first_name': update.message.from_user.first_name,
        'last_name': update.message.from_user.last_name
    }
    save_user_data(str(chat_id), user_data)

    await update.message.reply_text(f'Загрузка валютных пар...')
    await show_pairs(update, context, 0)

# Команда /about
async def about(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text('Это бот для предоставления курсов валют и другой информации. Разработан для демонстрации возможностей Telegram API.')

# Команда /commands
async def commands(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    commands_text = (
        "/start - Начать работу с ботом\n"
        "/about - Информация о боте\n"
        "/options - Опции бота\n"
        "/help - Получить помощь\n"
        "/commands - Список всех команд"
    )
    await update.message.reply_text(commands_text)

# Обработчик нажатий на кнопки
async def button(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    if query.data == 'help':
        help_message = "Здесь вы можете получить помощь по использованию бота. Используйте /start, чтобы начать работу, /about для получения информации о боте, /options для просмотра опций, и /commands для списка всех команд."
        await query.message.reply_text(help_message)

    elif query.data == 'about':
        about_message = 'Это бот для предоставления курсов валют и другой информации. Разработан для демонстрации возможностей Telegram API.'
        await query.message.reply_text(about_message)

    elif query.data == 'exchange_rate':
        await show_pairs(update, context, 0)

    elif query.data.startswith("pair_"):
        _, selected_pair, page = query.data.split("_")
        real_rate = get_real_exchange_rate(selected_pair)
        rate, direction = generate_exchange_rate()
        message = f"Валютная пара: {selected_pair}\nКурс: {rate}\nНаправление: {direction}"

        if selected_pair in currency_images:
            photo_url = currency_images[selected_pair]
            await query.message.reply_photo(photo=photo_url, caption=message)
        else:
            await query.edit_message_text(text=message)

        keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data=f"nav_{page}")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.message.reply_text("Выберите валютную пару:", reply_markup=reply_markup)

    elif query.data.startswith("nav_"):
        page = int(query.data.split("_")[1])
        await show_pairs(update, context, page)
    elif query.data == "ignore":
        pass

# Команда /options
async def options(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    keyboard = [
        [InlineKeyboardButton("Курс валют", callback_data='exchange_rate')],
        [InlineKeyboardButton("Помощь", callback_data='help')],
        [InlineKeyboardButton("О боте", callback_data='about')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text('Выберите опцию:', reply_markup=reply_markup)

# Функция для отображения валютных пар с навигацией
async def show_pairs(update: Update, context: ContextTypes.DEFAULT_TYPE, page: int) -> None:
    pairs_per_page = 10
    start_index = page * pairs_per_page
    end_index = start_index + pairs_per_page
    pairs_to_show = currency_pairs[start_index:end_index]

    keyboard = [
        [InlineKeyboardButton(pair, callback_data=f"pair_{pair}_{page}")] for pair in pairs_to_show
    ] + [
        [
            InlineKeyboardButton("⬅️ Назад", callback_data=f"nav_{page-1}") if page > 0 else InlineKeyboardButton("⬅️ Назад", callback_data="ignore"),
            InlineKeyboardButton("Вперед ➡️", callback_data=f"nav_{page+1}") if end_index < len(currency_pairs) else InlineKeyboardButton("Вперед ➡️", callback_data="ignore")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    if update.message:
        await update.message.reply_text('Выберите валютную пару:', reply_markup=reply_markup)
    elif update.callback_query:
        await update.callback_query.edit_message_text('Выберите валютную пару:', reply_markup=reply_markup)

# Функция для отправки сообщения всем пользователям
async def send_message_to_all(bot, message):
    file_path = 'user_data.json'
    if os.path.exists(file_path):
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read().strip()
                if content:
                    user_data = json.loads(content)
                else:
                    user_data = {}
        except (json.JSONDecodeError, FileNotFoundError) as e:
            logger.error(f"Ошибка при чтении файла user_data.json: {e}")
            user_data = {}

        for chat_id in user_data.keys():
            try:
                await bot.send_message(chat_id=int(chat_id), text=message)
            except telegram.error.TelegramError as e:
                logger.error(f"Не удалось отправить сообщение в чат {chat_id}: {e}")
    else:
        logger.error(f"Файл {file_path} не существует.")

# Функция для отправки случайного обновления курса валют
async def send_random_currency_update(bot):
    currency_pair = choice(currency_pairs)
    rate, direction = generate_exchange_rate()
    message = f'Курс валютной пары {currency_pair} составляет {rate} и он идет {direction}.'
    await send_message_to_all(bot, message)

# Запланированная задача
async def scheduled_task():
    logger.info("Выполняем запланированную задачу")

def start_scheduler():
    scheduler = AsyncIOScheduler()
    scheduler.add_job(scheduled_task, 'interval', minutes=60)
    scheduler.start()

# Функция для запуска бота и планирования задач
async def main(token: str):
    bot = Bot(token=token)
    application = Application.builder().token(token).build()

    application.add_handler(CommandHandler('start', start))
    application.add_handler(CommandHandler('about', about))
    application.add_handler(CommandHandler('options', options))
    application.add_handler(CallbackQueryHandler(button))
    application.add_handler(CommandHandler('help', about))
    application.add_handler(CommandHandler('commands', commands))

    await application.initialize()
    await application.start()
    print("Бот запущен")
    await application.updater.start_polling()

    start_scheduler()

    while True:
        await send_random_currency_update(bot)
        await asyncio.sleep(uniform(10, 60) * 60)

if __name__ == '__main__':
    token = '7340454174:AAH6sYIOaCIsumXy2OAK81-CnoyBoU-ePNw'

    try:
        asyncio.run(main(token))
    except RuntimeError as e:
        if str(e) == "This event loop is already running":
            loop = asyncio.get_running_loop()
            loop.create_task(main(token))
        else:
            raise