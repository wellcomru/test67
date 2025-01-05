import logging
import asyncio
import aiohttp
import re
from typing import Dict

from telegram import (
    Update,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    KeyboardButton,
    ReplyKeyboardMarkup,
)
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    CallbackContext,
    filters,
)
from telegram.error import BadRequest, TelegramError
from logging.handlers import RotatingFileHandler

# --------------------- НАСТРОЙКА ЛОГИРОВАНИЯ ---------------------
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

handler = RotatingFileHandler("bot.log", maxBytes=5*1024*1024, backupCount=5)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)

# --------------------- КОНСТАНТЫ ---------------------
APPS_SCRIPT_URL = "https://script.google.com/macros/s/AKfycbyqp0YYSSXL5eNoC3HFYJPo8QMVE4hVxHBeN9nes6dtvo8dpSFPciZEcijHTcYTgj8K/exec"  # <-- Укажите ваш URL
BOT_TOKEN = "7507339261:AAFCLBJT7m8jHMPxKcpTqpWkMaXQbbwWRks"                                            # <-- Укажите ваш токен

GROUP_CHAT_ID = -1002429928901      # ID вашей группы/супергруппы
ADMIN_CHAT_IDS = [418838097, 216931773]  # Список chat_id админов

FIELDS = [
    "Аниматор",
    "Ансамбль/Коллектив",
    "Аренда мебели",
    "Шатров",
    "Другой инвентарь",
    "Артист оригинального жанра",
    "База отдыха",
    "Отель",
    "Гостевой дом",
    "Ведущий",
    "Визажист",
    "Hair",
    "Стилист",
    "Вокалист",
    "Музыкант",
    "Кавер группа",
    "Ди-джей",
    "Звукооператор",
    "Дизайн",
    "Motion",
    "Брендинг",
    "Кейтеринг",
    "Кондитер",
    "Food флорист",
    "Маркетолог",
    "HR & PR специалист",
    "Организатор",
    "Координатор",
    "Ресторан",
    "Банкет-Холл",
    "Технические службы",
    "Свет",
    "Звук",
    "Сцена",
    "Транспорт",
    "Наземный",
    "Водный",
    "Воздушный",
    "Туризм",
    "Туры",
    "Гиды",
    "Агенты",
    "Флористика",
    "Декор",
    "Фотограф",
    "Видеограф",
    "Мобильная съёмка",
    "Заказчик",
    "Другое"
]

RULES_TEXT = (
    "{name},здесь вы найдёте любого "
    "специалиста в области развлечений, туризма и креатива.\n\n"
    "Чтобы наша с Вами коммуникация проходила позитивно и чат был максимально эффективным "
    "перед вступлением в группу ознакомьтесь с правилами чата.\n\n"
    "✅ ЧТО ЗДЕСЬ ДЕЛАТЬ МОЖНО:\n"
    "- Поиск нужного Вам специалиста (ведущие, организаторы мероприятий или туров, транспорт, мебель, артисты и др.)\n"
    "- Реклама и продажа своих товаров и услуг в профильных ветках\n"
    "- Для размещения рекламы мероприятий с указанием даты, взимается плата. Подробности в ветке «Афиша Мероприятий»\n"
    "- Обсуждения профильных тем, генерация идей и проектов, поиск единомышленников\n"
    "- Коллаборация. Предложения о сотрудничестве\n"
    "- Запросы советов и рекомендаций\n"
    "🔥 В спорных ситуациях, Вы можете излить душу в ветке «Черный список»\n\n"
    "🚫 ЗАПРЕЩЕНО:\n"
    "- Просить лайки, голоса и т. д.\n"
    "- Организовывать сбор денежных средств\n"
    "- Приглашать участников в группы или другие чаты\n"
    "- Флуд и оскорбления, включая переход на личности\n"
    "- Дублирование (спам) информации в более чем 3-х ветках\n"
    "- Писать с CAPS LOCK\n"
    "- Отправлять более одного стикера подряд\n"
    "При присоединении к этому чату Вы соглашаетесь с предоставленными условиями.\n"
    "⚠️ Рекомендуем отключить уведомления, чтобы не отвлекаться.\n\n"
    "По всем вопросам писать @artemtiik\n\n"
    "Для того чтобы мы добавили Вас в чат нажмите на кнопку,что Вы ознакомлены с правилами чата.\n"
)

WELCOME_TEXT = (
    "Добро пожаловать в комьюнити Event_Irkutsk!\n"
    "Если наш чат окажется для Вас полезным и Вы будете регулярно находить заказы, зарабатывать и решать свои вопросы, "
    "мы будем признательны Вашей финансовой поддержке в любом эквиваленте. Ваши донаты позволят нам "
    "осуществлять администрирование площадки, а также организовывать различные события для индустрии.\n"
    "⚡️⚡️⚡️⚡️⚡️⚡️⚡️⚡️⚡️⚡️⚡️\n"
    "ВЫ МОЖЕТЕ ПЕРЕВЕСТИ ЛЮБУЮ СУММУ ПО ССЫЛКЕ\n"
    "https://eventirkutsk.ru/donations\n"
    "Благодарим Вас за поддержку и вклад в развитие нашего комьюнити!\n\n"
    "Вступить в чат! https://t.me/Event_Irkutsk"
)

# --------------------- ФУНКЦИИ ДЛЯ РАБОТЫ С GOOGLE APPS SCRIPT ---------------------
async def send_async_request(url: str, payload: Dict) -> Dict:
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload, timeout=10) as resp:
                if resp.status == 200:
                    return await resp.json()
                else:
                    text = await resp.text()
                    logger.error(f"Ошибка запроса к {url}: {resp.status}, {text}")
                    return {}
    except Exception as ex:
        logger.error(f"Ошибка при запросе к {url}: {ex}")
        return {}

async def is_user_in_gsheets(user_id: int) -> bool:
    payload = {"action": "is_user_authorized", "chat_id": str(user_id)}
    data = await send_async_request(APPS_SCRIPT_URL, payload)
    return data.get("authorized", False)

def check_spam(message_text: str) -> bool:
    spam_patterns = [
        r"заработок\sбез\sвложений",
        r"быстрые\sденьги",
        r"финансовая\sпирамида",
        r"раздача\sденег",
        r"продвижение\sканала",
        r"накрутка",
        r"пассивный\sдоход",
        r"заработок\sбез\sвложений",
        r"быстрые\sденьги",
        r"финансовая\sпирамида",
        r"раздача\sденег",
        r"продвижение\sканала",
        r"накрутка",
        r"пассивный\sдоход",
        r"сво",
        r"путин",
        r"заработай\sпрямо\sсейчас",
        r"доход\sна\sавтомате",
        r"быстрая\sнакрутка",
        r"схемы\sзаработка",
        r"продажа\sбазы\sконтактов",
        r"легкие\sденьги",
        r"вложи\sи\sзаработай",
        r"получи\sденьги\sпрямо\sсейчас",
        r"криптовалюта\sбез\sвложений",
        r"финансовая\sсвобода",
        r"автоматический\sзаработок",
        r"халява",
        r"раскрутка\sаккаунта",
        r"заработок\sбез\sусилий",
        r"в\sтренды\sютуб",
        r"мошенничество",
        r"пассивный\sдоход\s2023",
        r"вывод\sсредств\sза\s5\sминут",
        r"беспроигрышные\sставки",
        r"скачать\sпрограмму\sдля\sзаработка",
        r"работа\sна\sдому",
        r"деньги\sбез\sобязательств",
        r"деньги\sздесь\sи\sсейчас"
    ]
    msg_lower = message_text.lower()
    return any(re.search(pattern, msg_lower) for pattern in spam_patterns)

# --------------------- УДАЛЕНИЕ СООБЩЕНИЙ ---------------------
async def delete_message_job(context: CallbackContext):
    job = context.job
    chat_id = job.data["chat_id"]
    message_id = job.data["message_id"]
    try:
        await context.bot.delete_message(chat_id=chat_id, message_id=message_id)
        logger.info(f"Уведомление бота (message_id={message_id}) удалено из чата {chat_id}")
    except TelegramError as e:
        logger.warning(f"Не удалось удалить уведомление (message_id={message_id}): {e}")

# --------------------- ОБРАБОТЧИКИ СООБЩЕНИЙ ---------------------
async def text_handler(update: Update, context: CallbackContext):
    if update.effective_chat.type in ("group", "supergroup"):
        await handle_group_message(update, context)
    elif update.effective_chat.type == "private":
        await handle_private_message(update, context)
    else:
        logger.info(f"Сообщение из неподдерживаемого типа чата: {update.effective_chat.type}")

async def handle_group_message(update: Update, context: CallbackContext):
    chat_id = update.effective_chat.id
    text = update.message.text
    real_user_id = update.effective_user.id

    username = update.effective_user.username
    first_name = update.effective_user.first_name
    mention_name = f"@{username}" if username else first_name or str(real_user_id)

    if not await is_user_in_gsheets(real_user_id):
        try:
            await update.message.delete()
        except TelegramError as e:
            logger.error(f"Не удалось удалить сообщение неавторизованного: {e}")

        warn_msg = await update.effective_chat.send_message(
            text=(
                f"Пользователь {mention_name}, вы ещё не авторизованы в чате.\n"
                f"Пройдите авторизацию через бота "
                f'<a href="t.me/Event_Irkutsk_Bot">@antyspamevent_bot</a>.'
            ),
            parse_mode="HTML",
            message_thread_id=update.message.message_thread_id
        )

        context.application.job_queue.run_once(
            delete_message_job,
            when=30,
            data={"chat_id": chat_id, "message_id": warn_msg.message_id}
        )
        return

    if check_spam(text):
        try:
            await update.message.delete()
        except TelegramError as e:
            logger.error(f"Не удалось удалить спам-сообщение: {e}")

        warns = context.user_data.get("spam_warnings", 0) + 1
        context.user_data["spam_warnings"] = warns
        if warns == 1:
            spam_msg = await update.effective_chat.send_message(
                text=f"{mention_name}, это сообщение похоже на спам. Предупреждение №1.",
                message_thread_id=update.message.message_thread_id
            )
            payload = {"action": "warn_spammer", "chat_id": real_user_id, "warns": warns}
            await send_async_request(APPS_SCRIPT_URL, payload)
        else:
            try:
                await update.effective_chat.ban_member(real_user_id)
                ban_msg = await update.effective_chat.send_message(
                    text=f"{mention_name} заблокирован за повторный спам.",
                    message_thread_id=update.message.message_thread_id
                )
                payload = {"action": "block_spammer", "chat_id": real_user_id}
                await send_async_request(APPS_SCRIPT_URL, payload)
            except TelegramError as e:
                logger.error(f"Не удалось забанить пользователя {real_user_id}: {e}")

async def handle_private_message(update: Update, context: CallbackContext):
    user_id = update.effective_chat.id
    text = update.message.text
    state = context.user_data.get("state", "")

    if context.user_data.get("registered"):
        logger.info(f"Пользователь {user_id} уже зарегистрирован, игнорируем.")
        return

    if state == "waiting_for_full_name":
        full_name = text.strip().split()
        if len(full_name) < 2:
            await update.message.reply_text(
                "Пожалуйста, введите **минимум** имя и фамилию (два слова).\n\n"
                "Например: `Иван Иванов`",
                parse_mode="Markdown"
            )
            return

        first_name = full_name[0]
        last_name = " ".join(full_name[1:])
        context.user_data["first_name"] = first_name
        context.user_data["last_name"] = last_name

        context.user_data["state"] = "waiting_for_phone"
        await update.message.reply_text(
            "Спасибо! Теперь укажите ваш номер телефона, нажав кнопку снизу:",
            reply_markup=ReplyKeyboardMarkup(
                [[KeyboardButton("Отправить контакт", request_contact=True)]],
                resize_keyboard=True,
                one_time_keyboard=True,
            )
        )
        return

    if state == "waiting_for_phone":
        await update.message.reply_text(
            "Пожалуйста, нажмите кнопку «Отправить контакт».\n"
            "Ввод номера вручную отключён."
        )
        return

    if user_id in ADMIN_CHAT_IDS:
        await handle_admin_message(update, context)
        return

    logger.info(f"Неожиданное сообщение в личке от {user_id}, state={state}: {text}")

async def handle_admin_message(update: Update, context: CallbackContext):
    user_id = update.effective_chat.id
    text = update.message.text
    state = context.user_data.get("state", "")

    if state == "admin_typing_msg_all":
        msg_to_send = text
        await update.message.reply_text("Рассылаем сообщение всем...")
        await send_message_to_all(msg_to_send, context)
        await update.message.reply_text("Готово! Сообщение отправлено всем.")
        context.user_data["state"] = ""
        return

    if state == "admin_typing_msg_cats":
        selected_cats = context.user_data.get("admin_selected_categories", [])
        if not selected_cats:
            await update.message.reply_text("Не выбрано ни одной категории. Попробуйте снова.")
            context.user_data["state"] = ""
            return

        msg_to_send = text
        await update.message.reply_text(
            f"Рассылаем сообщение для выбранных категорий: {', '.join(selected_cats)}"
        )
        for cat in selected_cats:
            await send_message_to_category(cat, msg_to_send, context)
            await asyncio.sleep(0.1)
        await update.message.reply_text("Готово! Сообщения отправлены выбранным категориям✅.")
        context.user_data["state"] = ""
        context.user_data["admin_selected_categories"] = []
        return

    if state == "admin_unblock_user":
        try:
            user_to_unblock = int(text)
            try:
                await context.bot.unban_chat_member(chat_id=GROUP_CHAT_ID, user_id=user_to_unblock)
                await update.message.reply_text(f"Пользователь {user_to_unblock} разблокирован.")
            except TelegramError as ex:
                logger.error(f"Ошибка разблокировки: {ex}")
                await update.message.reply_text("Ошибка при разблокировке.")

            payload = {"action": "unblock_spammer", "chat_id": user_to_unblock}
            await send_async_request(APPS_SCRIPT_URL, payload)
        except ValueError:
            await update.message.reply_text("Некорректный chat_id. Попробуйте снова.")
        context.user_data["state"] = ""
        return

    logger.info(f"Неожиданное админское сообщение от {user_id}, state={state}: {text}")

# --------------------- КОМАНДА /START ---------------------
async def start(update: Update, context: CallbackContext):
    user_id = update.effective_chat.id
    logger.info(f"/start от user_id={user_id}")

    # Если админ - сразу админ-меню
    if user_id in ADMIN_CHAT_IDS:
        await admin_menu(update, context)
        return

    # Сохраняем имя (если есть)
    if update.effective_user:
        context.user_data["name"] = update.effective_user.first_name or "NoName"
    else:
        context.user_data["name"] = "Unknown"

    # 1. Выводим приветствие и две кнопки: ссылка на оферту и "Начать регистрацию"
    greeting_text = (
        f"Привет, {context.user_data['name']}!\n\n"
        "Перед началом регистрации, пожалуйста, ознакомьтесь с офертой. "
        "Нажимая «Начать регистрацию», Вы соглашаетесь с условиями оферты:\n"
        "https://eventirkutsk.ru/privacy\n\n"
        "Чтобы продолжить, воспользуйтесь кнопками ниже:"
    )

    kb = [
        [
            InlineKeyboardButton("Посмотреть оферту", url="https://eventirkutsk.ru/privacy"),
            InlineKeyboardButton("Начать регистрацию", callback_data="start_registration")
        ]
    ]
    await update.message.reply_text(
        greeting_text,
        reply_markup=InlineKeyboardMarkup(kb)
    )

    # Устанавливаем состояние, чтобы дождаться нажатия "Начать регистрацию"
    context.user_data["state"] = "greeting_shown"

# --------------------- АДМИН-МЕНЮ ---------------------
async def admin_menu(update: Update, context: CallbackContext):
    user_id = update.effective_chat.id
    admin_kb = [
        [InlineKeyboardButton("Отправить сообщение", callback_data="send_message")],
        [InlineKeyboardButton("Разблокировать пользователя", callback_data="unblock_user")],
        [InlineKeyboardButton("Кнопка 1", callback_data="some_other_button1")],
        [InlineKeyboardButton("Кнопка 2", callback_data="some_other_button2")],
        [InlineKeyboardButton("Кнопка 3", callback_data="some_other_button3")],
    ]
    await update.message.reply_text(
        f"Админ-меню (chat_id={user_id}):",
        reply_markup=InlineKeyboardMarkup(admin_kb)
    )

# --------------------- ВСПОМОГАТЕЛЬНАЯ ФУНКЦИЯ: генерация клавиатуры с галочками ---------------------
def generate_fields_keyboard(selected_fields):
    """Генерируем инлайн-клавиатуру со списком FIELDS, проставляя ✅ для выбранных."""
    keyboard = []
    row = []
    for i, field in enumerate(FIELDS):
        text = field + (" ✅" if field in selected_fields else "")
        row.append(InlineKeyboardButton(text, callback_data=f"field_toggle_{i}"))
        if len(row) == 2:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)

    keyboard.append([InlineKeyboardButton("Готово", callback_data="fields_done")])
    return InlineKeyboardMarkup(keyboard)

def generate_admin_categories_keyboard(selected_cats):
    """Генерируем инлайн-клавиатуру для выбора категорий админом."""
    keyboard = []
    row = []
    for i, cat in enumerate(FIELDS):
        text = cat + (" ✅" if cat in selected_cats else "")
        row.append(InlineKeyboardButton(text, callback_data=f"admin_cat_toggle_{i}"))
        if len(row) == 2:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)

    keyboard.append([InlineKeyboardButton("Готово", callback_data="admin_cats_done")])
    return InlineKeyboardMarkup(keyboard)

# --------------------- CALLBACK ---------------------
async def callback_handler(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()
    user_id = query.message.chat.id
    data = query.data
    state = context.user_data.get("state", "")

    logger.info(f"Callback '{data}' от user_id={user_id}, state={state}")

    # --- Обработка нажатия "Начать регистрацию" после приветствия ---
    if state == "greeting_shown" and data == "start_registration":
        # Переходим к отображению правил (ранее было в /start)
        rules_text = RULES_TEXT.replace("{name}", context.user_data["name"])
        await query.message.reply_text(
            rules_text,
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("Я ознакомлен/а✅", callback_data="rules_confirmed")]]
            )
        )
        context.user_data["state"] = "waiting_for_rules_confirmation"
        return

    # 2. Подтверждение ознакомления с правилами
    if state == "waiting_for_rules_confirmation" and data == "rules_confirmed":
        # Изначально пользователь не выбрал ничего
        context.user_data["selected_fields"] = []
        await query.message.reply_text(
            "Ваша заявка одобрена!\n"
            "Выберите из списка, к какой сфере вы относитесь (можно несколько) и после этого нажмите кнопку **готово**.",
            reply_markup=generate_fields_keyboard(context.user_data["selected_fields"]),
            parse_mode="Markdown"
        )
        context.user_data["state"] = "waiting_for_field"
        return

    # 3. Множественный выбор поля (сферы)
    if state == "waiting_for_field" and data.startswith("field_toggle_"):
        try:
            idx = int(data.split("_")[-1])
            field = FIELDS[idx]
        except (ValueError, IndexError):
            logger.error(f"Некорректная сфера: {data}")
            await query.message.reply_text("Некорректный выбор сферы. Попробуйте снова.")
            return

        selected = context.user_data.get("selected_fields", [])
        if field in selected:
            selected.remove(field)
        else:
            selected.append(field)

        context.user_data["selected_fields"] = selected
        await query.message.edit_text(
            text="Выберите из списка, к какой сфере вы относитесь (можно несколько):",
            reply_markup=generate_fields_keyboard(selected)
        )
        return

    # 4. Пользователь закончил выбор сфер
    if state == "waiting_for_field" and data == "fields_done":
        selected = context.user_data.get("selected_fields", [])
        if not selected:
            await query.message.reply_text(
                "Вы не выбрали ни одной сферы. Пожалуйста, выберите хотя бы одну."
            )
            return

        context.user_data["field"] = ", ".join(selected)
        context.user_data["state"] = "waiting_for_full_name"
        await query.message.reply_text(
            "Отлично! Пожалуйста, введите Ваше имя и фамилию одним сообщением.\n\n"
            "Например: `Иван Иванов`",
            parse_mode="Markdown"
        )
        return

    # -----------------------------------
    #           БЛОК АДМИНА
    # -----------------------------------
    if user_id in ADMIN_CHAT_IDS:
        # Нажатие на "Отправить сообщение"
        if data == "send_message":
            admin_buttons = [
                [InlineKeyboardButton("Всем участникам", callback_data="admin_send_all")],
                [InlineKeyboardButton("Выбрать категории", callback_data="admin_select_cats")]
            ]
            await query.message.reply_text(
                "Выберите способ рассылки:",
                reply_markup=InlineKeyboardMarkup(admin_buttons)
            )
            return

        if data == "admin_send_all":
            context.user_data["state"] = "admin_typing_msg_all"
            await query.message.reply_text("Введите текст сообщения, которое хотите отправить всем участникам:")
            return

        if data == "admin_select_cats":
            context.user_data["admin_selected_categories"] = []
            await query.message.reply_text(
                "Выберите категории, которым хотите отправить сообщение (можно несколько):",
                reply_markup=generate_admin_categories_keyboard(context.user_data["admin_selected_categories"])
            )
            return

        if data.startswith("admin_cat_toggle_"):
            try:
                idx = int(data.split("_")[-1])
                cat = FIELDS[idx]
            except (ValueError, IndexError):
                logger.error(f"Ошибка admin_cat_toggle: {data}")
                await query.message.reply_text("Некорректная категория. Попробуйте снова.")
                return

            selected_cats = context.user_data.get("admin_selected_categories", [])
            if cat in selected_cats:
                selected_cats.remove(cat)
            else:
                selected_cats.append(cat)

            context.user_data["admin_selected_categories"] = selected_cats

            await query.message.edit_text(
                text="Выберите категории, которым хотите отправить сообщение (можно несколько):",
                reply_markup=generate_admin_categories_keyboard(selected_cats)
            )
            return

        if data == "admin_cats_done":
            selected_cats = context.user_data.get("admin_selected_categories", [])
            if not selected_cats:
                await query.message.reply_text("Вы не выбрали ни одной категории.")
                return

            context.user_data["state"] = "admin_typing_msg_cats"
            await query.message.reply_text(
                f"Вы выбрали категории: {', '.join(selected_cats)}.\n"
                "Введите текст сообщения, которое хотите разослать этим категориям:"
            )
            return

        if data == "unblock_user":
            context.user_data["state"] = "admin_unblock_user"
            await query.message.reply_text("Введите chat_id пользователя, которого нужно разблокировать:")
            return

        if data == "some_other_button1":
            await query.message.reply_text("Функция пока не реализована. Пожалуйста, попробуйте позже.")
            return

        if data == "some_other_button2":
            await query.message.reply_text("Функция пока не реализована. Пожалуйста, попробуйте позже.")
            return

        if data == "some_other_button3":
            await query.message.reply_text("Функция пока не реализована. Пожалуйста, попробуйте позже.")
            return

    logger.warning(f"Неожиданный callback data={data}, state={state}")

# --------------------- ОБРАБОТКА КОНТАКТА ---------------------
async def contact_handler(update: Update, context: CallbackContext):
    chat_id = update.effective_chat.id
    state = context.user_data.get("state", "")

    if context.user_data.get("registered"):
        logger.info(f"Пользователь {chat_id} уже зарегистрирован, игнорируем повторный контакт.")
        return

    if state == "waiting_for_phone":
        contact = update.message.contact
        if contact:
            context.user_data["phone"] = contact.phone_number
            await save_and_finish(update, context)
        else:
            logger.warning("Контакт отсутствует или None")
            await update.message.reply_text("Контакт не получен. Пожалуйста, нажмите кнопку «Отправить контакт».")
        return

# --------------------- ЗАВЕРШЕНИЕ РЕГИСТРАЦИИ ---------------------
async def save_and_finish(update: Update, context: CallbackContext):
    chat_id = update.effective_chat.id

    first_name = context.user_data.get("first_name", "NoName")
    last_name = context.user_data.get("last_name", "NoSurname")
    phone = context.user_data.get("phone", "")
    field = context.user_data.get("field", "")

    # Объединяем имя и фамилию
    name = f"{first_name} {last_name}".strip()

    payload = {
        "action": "save_user_data",
        "chat_id": str(chat_id),
        "name": name,
        "phone": phone,
        "field": field
    }
    try:
        data = await send_async_request(APPS_SCRIPT_URL, payload)
        if data.get("status") == "ok":
            logger.info(f"Данные пользователя {chat_id} успешно сохранены.")
        else:
            logger.error(f"Ошибка сохранения данных для {chat_id}: {data}")
            await update.message.reply_text("Произошла ошибка при сохранении данных. Пожалуйста, попробуйте позже.")
            return
    except Exception as e:
        logger.error(f"Ошибка при отправке данных в Apps Script: {e}")
        await update.message.reply_text("Произошла ошибка при сохранении данных. Пожалуйста, попробуйте позже.")
        return

    context.user_data["registered"] = True

    if await is_user_in_gsheets(chat_id):
        await try_invite_user_to_group(context, chat_id)

    await update.message.reply_text(
        WELCOME_TEXT,
        reply_markup=InlineKeyboardMarkup(
            [[InlineKeyboardButton("Вступить в чат!", url="https://t.me/Event_Irkutsk")]]
        )
    )
    context.user_data.pop("state", None)
    logger.info(f"Пользователь {chat_id} завершил регистрацию.")

# --------------------- ПРИГЛАШЕНИЕ В ГРУППУ ---------------------
async def try_invite_user_to_group(context: CallbackContext, user_id: int):
    try:
        member = await context.bot.get_chat_member(GROUP_CHAT_ID, user_id)
        if member.status in ["kicked", "left"]:
            await context.bot.unban_chat_member(chat_id=GROUP_CHAT_ID, user_id=user_id)
            logger.info(f"Пользователь {user_id} приглашён в группу {GROUP_CHAT_ID}.")
        else:
            logger.info(f"Пользователь {user_id} уже является участником группы.")
    except BadRequest as e:
        if "not kicked" in str(e).lower():
            logger.info(f"Пользователь {user_id} уже является участником группы.")
        else:
            logger.error(f"BadRequest при приглашении user_id={user_id}: {e}")
    except TelegramError as e:
        logger.error(f"Не удалось разбанить/пригласить user_id={user_id}: {e}")

# --------------------- РАССЫЛКИ ---------------------
async def send_message_to_all(text_to_send: str, context: CallbackContext) -> None:
    payload = {"action": "get_all_chat_ids"}
    data = await send_async_request(APPS_SCRIPT_URL, payload)
    chat_ids = data.get("chat_ids", [])

    tasks = []
    for cid in chat_ids:
        tasks.append(send_message(cid, text_to_send, context))
        await asyncio.sleep(0.05)

    await asyncio.gather(*tasks)

async def send_message_to_category(category: str, text_to_send: str, context: CallbackContext) -> None:
    payload = {"action": "get_chat_ids_by_category", "category": category}
    data = await send_async_request(APPS_SCRIPT_URL, payload)
    chat_ids = data.get("chat_ids", [])

    tasks = []
    for cid in chat_ids:
        tasks.append(send_message(cid, text_to_send, context))
        await asyncio.sleep(0.05)

    await asyncio.gather(*tasks)

async def send_message(chat_id: int, text: str, context: CallbackContext):
    try:
        await context.bot.send_message(chat_id=chat_id, text=text)
        logger.info(f"Сообщение успешно отправлено пользователю {chat_id}.")
    except TelegramError as ex:
        logger.error(f"Ошибка отправки сообщения пользователю {chat_id}: {ex}")

# --------------------- ГЛОБАЛЬНЫЙ ОБРАБОТЧИК ОШИБОК ---------------------
async def error_handler(update: object, context: CallbackContext):
    logger.error(msg="Exception while handling an update:", exc_info=context.error)
    if isinstance(update, Update):
        try:
            await update.effective_message.reply_text("Произошла ошибка при обработке вашего запроса.")
        except TelegramError:
            pass

# --------------------- ГЛАВНАЯ ФУНКЦИЯ ---------------------
def main():
    logger.info("Запуск бота...")
    application = Application.builder().token(BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("admin", admin_menu))
    application.add_handler(CallbackQueryHandler(callback_handler))
    application.add_handler(MessageHandler(filters.CONTACT, contact_handler))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler))

    application.add_error_handler(error_handler)

    application.run_polling()
    logger.info("Бот остановлен.")

if __name__ == "__main__":
    main()
