import os
from flask import Flask, request, redirect, render_template, jsonify
from database import init_db, add_video, get_all_videos

app = Flask(__name__)
UPLOAD_FOLDER = 'static/videos'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

init_db()

@app.route('/', methods=['GET', 'POST'])
def upload_file():
    if request.method == 'POST':
        title = request.form.get('title')
        category = request.form.get('category')
        file = request.files.get('video')
        
        if file and file.filename:
            filename = file.filename
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(file_path)
            
            file_url = f"/static/videos/{filename}"
            add_video(title=title, category=category, file_url=file_url)
            return redirect('/')
            
    return render_template('index.html')

@app.route('/admin')
def admin_panel():
    videos = get_all_videos()
    return render_template('admin_site.html', videos=videos)

@app.route('/api/delete/<int:video_id>', methods=['POST'])
def delete_video(video_id):
    import sqlite3
    conn = sqlite3.connect('database.db', check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute('SELECT file_url FROM videos WHERE id = ?', (video_id,))
    row = cursor.fetchone()
    if row and row[0]:
        file_path = row[0].lstrip('/')
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
            except:
                pass
                
    cursor.execute('DELETE FROM videos WHERE id = ?', (video_id,))
    conn.commit()
    conn.close()
    return jsonify({'success': True})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)