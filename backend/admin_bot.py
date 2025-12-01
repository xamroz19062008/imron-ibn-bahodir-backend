from pathlib import Path
import os
import time
import requests

# === НАСТРОЙКИ ===
# Токен берём из переменной окружения BOT_TOKEN
BOT_TOKEN = os.environ.get("BOT_TOKEN")
if not BOT_TOKEN:
    raise RuntimeError("Не задан BOT_TOKEN в переменных окружения")

API_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"

BACKEND_URL = os.environ.get(
    "BACKEND_URL",
    "https://imron-ibn-bahodir-backend.onrender.com",
)
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


def fetch_leads(period: str | None) -> list[dict]:
    """
    period: None / 'today' / 'month' / 'year'
    """
    params = {
        "limit": 10,
    }
    if period:
        params["period"] = period

    try:
        resp = requests.get(
            f"{BACKEND_URL}/admin/leads",
            params=params,
            timeout=15,
        )
        data = resp.json()
        if not data.get("success"):
            print("Ошибка ответа backend:", data)
            return []
        return data.get("leads", [])
    except Exception as e:
        print("Ошибка запроса к backend:", e)
        return []


def format_leads(leads: list[dict]) -> str:
    if not leads:
        return "Записей не найдено."

    parts = []
    for row in leads:
        parts.append(
            (
                "🆕 <b>Заявка</b>\n"
                f"📅 <b>Дата:</b> {row.get('created_at','')}\n\n"
                f"👤 Имя: {row.get('name','')}\n"
                f"🏢 Компания: {row.get('company','')}\n"
                f"📞 Телефон: {row.get('phone','')}\n"
                f"📧 Email: {row.get('email','')}\n\n"
                f"📦 Объём: {row.get('volume','')}\n"
                f"🛠 Использование: {row.get('usage_purpose','')}\n\n"
                f"📝 Комментарий:\n{row.get('comment') or '—'}"
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
        leads = fetch_leads(None)
        send_message(chat_id, format_leads(leads))
        return

    if text == "📅 За сегодня":
        leads = fetch_leads("today")
        send_message(chat_id, format_leads(leads))
        return

    if text == "🗓 За этот месяц":
        leads = fetch_leads("month")
        send_message(chat_id, format_leads(leads))
        return

    if text == "📆 За этот год":
        leads = fetch_leads("year")
        send_message(chat_id, format_leads(leads))
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
