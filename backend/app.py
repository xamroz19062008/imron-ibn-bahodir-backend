import os
import sqlite3
from pathlib import Path
from datetime import datetime

import requests
from flask import Flask, request, jsonify
from flask_cors import CORS


# ===== ПУТЬ К БАЗЕ ДАННЫХ =====
BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "leads.db"   # leads.db лежит рядом с app.py
# ==============================


app = Flask(__name__)
CORS(app)

# ---------- ИНИЦИАЛИЗАЦИЯ БАЗЫ ----------
def init_db():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS leads (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            company TEXT,
            phone TEXT,
            email TEXT,
            volume TEXT,
            usage_purpose TEXT,
            comment TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """
    )
    conn.commit()
    conn.close()
    print(f"DB init OK, path = {DB_PATH}")


init_db()  # вызываем один раз при старте приложения
# ========================================


# ===== НАСТРОЙКИ БОТА =====
BOT_TOKEN = os.environ.get("BOT_TOKEN")

# Два администратора — сюда ставишь свои Telegram ID
ADMINS = [6746524257, 89028703]
# ==========================


# ---------- СОХРАНЕНИЕ В БАЗУ ----------
def save_lead(name, company, phone, email, volume, usage, comment):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute(
        """
        INSERT INTO leads (name, company, phone, email, volume, usage_purpose, comment, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            name,
            company,
            phone,
            email,
            volume,
            usage,
            comment,
            datetime.now().isoformat(),
        ),
    )

    conn.commit()
    conn.close()


# ---------- ОТПРАВКА В TELEGRAM ----------
def send_telegram(text: str):
    if not BOT_TOKEN:
        print("BOT_TOKEN не задан, Telegram-уведомление не отправлено")
        return

    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"

    for admin_id in ADMINS:
        try:
            resp = requests.post(
                url,
                json={
                    "chat_id": admin_id,
                    "text": text,
                    "parse_mode": "HTML",
                },
                timeout=15,
            )
            print("TG response:", admin_id, resp.status_code, resp.text)
        except Exception as e:
            print("Ошибка отправки в Telegram:", e)


# ---------- ROUTES ----------
@app.route("/", methods=["GET"])
def home():
    return "Backend работает! Telegram + DB OK"


@app.route("/lead", methods=["POST"])
def lead():
    try:
        data = request.get_json(force=True)

        name = data.get("name", "").strip()
        company = data.get("company", "").strip()
        phone = data.get("phone", "").strip()
        email = data.get("email", "").strip()
        volume = data.get("volume", "").strip()
        usage = data.get("usage", "").strip()
        comment = data.get("comment", "").strip()

        # простая проверка
        if not name or not phone:
            return (
                jsonify(
                    {
                        "success": False,
                        "message": "Имя и телефон обязательны",
                    }
                ),
                400,
            )

        # 1) сохраняем в базу
        save_lead(name, company, phone, email, volume, usage, comment)

        # 2) отправляем в Telegram
        text = f"""
<b>Новая заявка с сайта</b>

👤 Имя: {name}
🏢 Компания: {company}
📞 Телефон: {phone}
📧 Email: {email}

📦 Объём: {volume}
🛠 Использование: {usage}

📝 Комментарий:
{comment or "—"}
"""
        send_telegram(text)

        return jsonify({"success": True})

    except Exception as e:
        print("Ошибка в /lead:", e)
        return jsonify({"success": False, "message": "Ошибка сервера"}), 500


# ---------- ЗАПУСК ЛОКАЛЬНО ----------
if __name__ == "__main__":
    # Render передаёт порт в переменной окружения PORT
    port = int(os.environ.get("PORT", 5050))
    app.run(host="0.0.0.0", port=port)
