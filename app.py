from flask import Flask, render_template, request, redirect, session, url_for
from authlib.integrations.flask_client import OAuth
import sqlite3

app = Flask(__name__)
app.secret_key = 'секретный_ключ'
oauth = OAuth(app)

# OAuth конфиг
app.config['TWITCH_CLIENT_ID'] = 'ВАШ_TWITCH_CLIENT_ID'
app.config['TWITCH_CLIENT_SECRET'] = 'ВАШ_TWITCH_SECRET'
app.config['TWITCH_REDIRECT_URI'] = 'http://localhost:5000/twitch/callback'

app.config['GOOGLE_CLIENT_ID'] = 'ВАШ_GOOGLE_CLIENT_ID'
app.config['GOOGLE_CLIENT_SECRET'] = 'ВАШ_GOOGLE_SECRET'
app.config['GOOGLE_REDIRECT_URI'] = 'http://localhost:5000/youtube/callback'

twitch = oauth.register(
    name='twitch',
    client_id=app.config['TWITCH_CLIENT_ID'],
    client_secret=app.config['TWITCH_CLIENT_SECRET'],
    access_token_url='https://id.twitch.tv/oauth2/token',
    authorize_url='https://id.twitch.tv/oauth2/authorize',
    api_base_url='https://api.twitch.tv/helix/',
    client_kwargs={'scope': 'user:read:email'}
)

google = oauth.register(
    name='google',
    client_id=app.config['GOOGLE_CLIENT_ID'],
    client_secret=app.config['GOOGLE_CLIENT_SECRET'],
    access_token_url='https://oauth2.googleapis.com/token',
    authorize_url='https://accounts.google.com/o/oauth2/auth',
    api_base_url='https://www.googleapis.com/oauth2/v1/',
    client_kwargs={'scope': 'openid email profile https://www.googleapis.com/auth/youtube.readonly'}
)

def init_db():
    with sqlite3.connect("db.sqlite3") as conn:
        c = conn.cursor()
        c.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE,
                password TEXT,
                twitch_id TEXT,
                youtube_id TEXT
            )
        ''')
        conn.commit()

init_db()

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        with sqlite3.connect("db.sqlite3") as conn:
            try:
                conn.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, password))
                conn.commit()
                return redirect('/login')
            except:
                return "Пользователь уже существует"
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        with sqlite3.connect("db.sqlite3") as conn:
            cur = conn.execute("SELECT * FROM users WHERE username=? AND password=?", (username, password))
            user = cur.fetchone()
            if user:
                session['user_id'] = user[0]
                return redirect('/dashboard')
            else:
                return "Неверный логин или пароль"
    return render_template('login.html')

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect('/login')
    return render_template('dashboard.html')

@app.route('/connect/twitch')
def connect_twitch():
    return twitch.authorize_redirect(app.config['TWITCH_REDIRECT_URI'])

@app.route('/twitch/callback')
def twitch_callback():
    token = twitch.authorize_access_token()
    user_info = twitch.get('users').json()['data'][0]
    twitch_id = user_info['id']
    with sqlite3.connect("db.sqlite3") as conn:
        conn.execute("UPDATE users SET twitch_id=? WHERE id=?", (twitch_id, session['user_id']))
        conn.commit()
    return redirect('/dashboard')

@app.route('/connect/youtube')
def connect_youtube():
    return google.authorize_redirect(app.config['GOOGLE_REDIRECT_URI'])

@app.route('/youtube/callback')
def youtube_callback():
    token = google.authorize_access_token()
    user_info = google.get('userinfo').json()
    youtube_id = user_info['id']
    with sqlite3.connect("db.sqlite3") as conn:
        conn.execute("UPDATE users SET youtube_id=? WHERE id=?", (youtube_id, session['user_id']))
        conn.commit()
    return redirect('/dashboard')

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/login')

if __name__ == '__main__':
    app.run(debug=True)
