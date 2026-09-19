import sqlite3

def init_db():
    conn = sqlite3.connect('database.db', check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS videos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            category TEXT,
            file_id TEXT,       -- Telegram file_id (если загружено через бота)
            file_url TEXT       -- Ссылка на файл (если загружено через сайт)
        )
    ''')
    conn.commit()
    conn.close()

def add_video(title, category, file_id=None, file_url=None):
    conn = sqlite3.connect('database.db', check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute(
        'INSERT INTO videos (title, category, file_id, file_url) VALUES (?, ?, ?, ?)',
        (title, category, file_id, file_url)
    )
    conn.commit()
    conn.close()

def get_all_videos():
    conn = sqlite3.connect('database.db', check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute('SELECT id, title, category, file_id, file_url FROM videos')
    rows = cursor.fetchall()
    conn.close()
    return rows

def get_random_video():
    conn = sqlite3.connect('database.db', check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute('SELECT id, title, category, file_id, file_url FROM videos ORDER BY RANDOM() LIMIT 1')
    row = cursor.fetchone()
    conn.close()
    return row

def get_video_by_id(video_id):
    conn = sqlite3.connect('database.db', check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute('SELECT id, title, category, file_id, file_url FROM videos WHERE id = ?', (video_id,))
    row = cursor.fetchone()
    conn.close()
    return row

init_db()