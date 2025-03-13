import sqlite3

# SQLite 데이터베이스 연결 함수
def get_db_connection():
    conn = sqlite3.connect('emails.db')  # SQLite 데이터베이스 파일 연결
    conn.row_factory = sqlite3.Row  # 결과를 딕셔너리 형태로 반환
    return conn

## 테이블 생성
def create_table():
    conn = get_db_connection()
    conn.execute('''
    CREATE TABLE IF NOT EXISTS emails (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        uid TEXT NOT NULL,
        subject TEXT NOT NULL,
        sender TEXT NOT NULL,
        sender_email TEXT NOT NULL,
        date TEXT NOT NULL,
        body TEXT,
        html_body TEXT,
        spam INTEGER
    )
    ''')
    conn.commit()
    conn.close()

# 이메일 삽입 함수
def insert_email(uid, subject, sender, sender_email, date, body, html_body, spam=None):
    conn = get_db_connection()
    conn.execute('''
    INSERT INTO emails (uid, subject, sender, sender_email, date, body, html_body, spam)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', (uid, subject, sender, sender_email, date, body, html_body, spam))
    conn.commit()
    conn.close()