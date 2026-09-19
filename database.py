import sqlite3

def init_db():
    conn = sqlite3.connect('database.db', check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS videos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            category TEXT,
            file_id TEXT,        -- Telegram file_id (если загружено через бота)
            file_url TEXT,       -- Ссылка на файл (если загружено через сайт)
            views INTEGER DEFAULT 0 -- Счетчик просмотров
        )
    ''')
    conn.commit()
    conn.close()

def add_video(title, category, file_id=None, file_url=None):
    conn = sqlite3.connect('database.db', check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute(
        'INSERT INTO videos (title, category, file_id, file_url, views) VALUES (?, ?, ?, ?, 0)',
        (title, category, file_id, file_url)
    )
    conn.commit()
    conn.close()

def get_all_videos():
    conn = sqlite3.connect('database.db', check_same_thread=False)
    cursor = conn.cursor()
    # Возвращаем также количество просмотров (views)
    cursor.execute('SELECT id, title, category, file_id, file_url, views FROM videos')
    rows = cursor.fetchall()
    conn.close()
    return rows

def get_random_video():
    conn = sqlite3.connect('database.db', check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute('SELECT id, title, category, file_id, file_url, views FROM videos ORDER BY RANDOM() LIMIT 1')
    row = cursor.fetchone()
    conn.close()
    return row

def get_video_by_id(video_id):
    conn = sqlite3.connect('database.db', check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute('SELECT id, title, category, file_id, file_url, views FROM videos WHERE id = ?', (video_id,))
    row = cursor.fetchone()
    conn.close()
    return row

def increment_video_views(video_id):
    """Увеличивает счетчик просмотров видео на 1"""
    conn = sqlite3.connect('database.db', check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute('UPDATE videos SET views = views + 1 WHERE id = ?', (video_id,))
    conn.commit()
    conn.close()

def search_videos_db(query):
    """Ищет видео по названию (частичное совпадение) или точному ID"""
    conn = sqlite3.connect('database.db', check_same_thread=False)
    cursor = conn.cursor()
    
    # Ищем по вхождению в title (регистронезависимо в SQLite через LIKE) или точное совпадение id
    cursor.execute(
        'SELECT id, title, category, file_id, file_url, views FROM videos WHERE title LIKE ? OR id = ?',
        (f'%{query}%', query if query.isdigit() else -1)
    )
    rows = cursor.fetchall()
    conn.close()
    return rows

init_db()
