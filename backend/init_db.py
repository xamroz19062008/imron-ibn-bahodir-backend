from pathlib import Path
import sqlite3

# Путь к файлу базы данных (leads.db лежит рядом с init_db.py / app.py)
BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "leads.db"


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
    print(f"База данных создана/обновлена по пути: {DB_PATH}")


if __name__ == "__main__":
    init_db()
