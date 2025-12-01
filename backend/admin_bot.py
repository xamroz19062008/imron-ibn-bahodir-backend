from pathlib import Path
import os
import time
import requests
import sqlite3

# === НАСТРОЙКИ ===
# Токен берём из переменной окружения BOT_TOKEN
BOT_TOKEN = os.environ.get("BOT_TOKEN")
if not BOT_TOKEN:
    raise RuntimeError("Не задан BOT_TOKEN в переменных окружения")

API_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"

# БД лежит рядом с этим файлом
DB_PATH = Path(__file__).resolve().parent / "leads.db"
# ================


def send_message(chat_id, text, reply_markup=None):
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML",
    }
    if reply_markup:
        payload["reply_markup"] = reply_markup

    requests.post(f"{API_URL}/sendMessage", json=payload, timeout=20)


def build_main_keyboard():
    return {
        "keyboard": [
            [{"text": "📋 Все заявки (последние 10)"}],
            [
                {"text": "📅 За сегодня"},
                {"text": "🗓 За этот месяц"},
            ],
            [{"text": "📆 За этот год"}],
        ],
        "resize_keyboard": True,
    }


def fetch_leads(where_clause=None, params=()):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    query = """
        SELECT
            name,
            company,
            phone,
            email,
            volume,
            usage_purpose,
            comment,
            datetime(created_at, 'localtime') AS created_at
        FROM leads
    """
    if where_clause:
        query += " WHERE " + where_clause

    query += " ORDER BY created_at DESC LIMIT 10"

    cur.execute(query, params)
    rows = cur.fetchall()
    conn.close()
    return rows


def format_leads(rows):
    if not rows:
        return "Записей не найдено."

    parts = []
    for row in rows:
        parts.append(
            (
                "🆕 <b>Заявка</b>\n"
                f"📅 <b>Дата:</b> {row['created_at']}\n\n"
                f"👤 Имя: {row['name']}\n"
                f"🏢 Компания: {row['company']}\n"
                f"📞 Телефон: {row['phone']}\n"
                f"📧 Email: {row['email']}\n\n"
                f"📦 Объём: {row['volume']}\n"
                f"🛠 Использование: {row['usage_purpose']}\n\n"
                f"📝 Комментарий:\n{row['comment'] or '—'}"
            )
        )

    return "\n\n" + "\n\n".join(parts)


def handle_text(chat_id, text):
    text = text.strip()

    if text == "/start":
        send_message(
            chat_id,
            "Привет! Это панель заявок с сайта.\nВыберите действие:",
            reply_markup=build_main_keyboard(),
        )
        return

    if text.startswith("📋 Все заявки"):
        rows = fetch_leads()
        send_message(chat_id, format_leads(rows))
        return

    if text == "📅 За сегодня":
        rows = fetch_leads("DATE(created_at, 'localtime') = DATE('now','localtime')")
        send_message(chat_id, format_leads(rows))
        return

    if text == "🗓 За этот месяц":
        rows = fetch_leads(
            "strftime('%Y-%m', created_at, 'localtime') = strftime('%Y-%m','now','localtime')"
        )
        send_message(chat_id, format_leads(rows))
        return

    if text == "📆 За этот год":
        rows = fetch_leads(
            "strftime('%Y', created_at, 'localtime') = strftime('%Y','now','localtime')"
        )
        send_message(chat_id, format_leads(rows))
        return

    # любое другое сообщение
    send_message(
        chat_id,
        "Я вас не понял 🙂 Выберите действие на клавиатуре.",
        reply_markup=build_main_keyboard(),
    )


def main():
    print("Admin-бот запущен")
    offset = None

    while True:
        try:
            resp = requests.get(
                f"{API_URL}/getUpdates",
                params={"timeout": 60, "offset": offset},
                timeout=70,
            ).json()

            for upd in resp.get("result", []):
                offset = upd["update_id"] + 1

                message = upd.get("message") or upd.get("edited_message")
                if not message:
                    continue

                chat_id = message["chat"]["id"]
                text = message.get("text", "")

                if not text:
                    continue

                handle_text(chat_id, text)

        except Exception as e:
            print("Ошибка в боте:", e)
            time.sleep(3)


if __name__ == "__main__":
    main()
