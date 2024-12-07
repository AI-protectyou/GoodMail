import os
import time
from flask import Flask, jsonify, render_template, url_for, request, redirect, session, flash, send_from_directory
from dotenv import load_dotenv
import imap_email_reader
import key_loader
import rsa_cipher
from db_utils import get_db_connection, insert_email, create_table
import joblib
import numpy as np
from bs4 import BeautifulSoup
from flask_swagger_ui import get_swaggerui_blueprint

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'your_default_secret_key')  # .env 파일에서 비밀 키를 가져오거나 기본값을 사용

model = joblib.load('spam_classifier_model.pkl')
tfidf_vectorizer = joblib.load('vectorizer.pkl')

imap_connection = None
server_name = decrypted_email = decrypted_password = None
user_email = None

# Swagger 설정
SWAGGER_URL = '/swagger'  # Swagger UI에 접근할 URL
API_URL = '/swagger.json'  # Swagger 파일 경로

swaggerui_blueprint = get_swaggerui_blueprint(
    SWAGGER_URL,
    API_URL,
    config={
        'app_name': "이메일 관리 API"
    }
)
app.register_blueprint(swaggerui_blueprint, url_prefix=SWAGGER_URL)
# Swagger JSON 제공
@app.route(API_URL)
def swagger_json():
    return send_from_directory('.', 'swagger.json')

@app.route("/")
def home():
    return render_template("login.html")

"""메일 리스트"""
@app.route("/mailbox")
def mailbox():
    return render_template("mail_list.html", user_email=user_email)

@app.route("/api/content/<int:id>")
def mail_content(id):
    # 데이터베이스 연결 및 데이터 가져오기
    conn = get_db_connection()
    if conn is None:
        return jsonify({"status": "error", "message": "Database connection failed"}), 500

    try:
        email_data = conn.execute(
            'SELECT subject, sender, sender_email, date, html_body, spam FROM emails WHERE id = ?',
            (id,)
        ).fetchone()
    except Exception as e:
        return jsonify({"status": "error", "message": f"Database query failed: {str(e)}"}), 500
    conn.close()

    if not email_data:
        return jsonify({"status": "error", "message": "Email not found."}), 404

    # 데이터를 딕셔너리로 변환하여 템플릿에 전달
    email_dict = dict(email_data)
    print(email_dict)
    try:
        return render_template("mail_content.html", user_email=user_email, email=email_dict)
    except Exception as e:
        return jsonify({"status": "error", "message": f"Template rendering failed: {str(e)}"}), 500

@app.route("/api/mail", methods=["GET"])
def show_mail():
    # db에 있는 내용 다 가져오기
    conn = get_db_connection()
    emails = conn.execute('SELECT id, uid, subject, sender, sender_email, date, spam FROM emails ORDER BY id DESC').fetchall()
    conn.close()

    if not emails:
        return jsonify({"status": "success", "emails": [], "message": "No emails found."}), 204

    return jsonify({"status": "success", "emails": [dict(email) for email in emails]})

@app.route("/api/new_mail", methods=["GET"]) ## api 이름 바꾸기
def fetch_emails():
    print("Fetching emails...")
    global imap_connection
    imap_connection = imap_email_reader.login_to_imap(server_name, decrypted_email, decrypted_password)
    print(f"IMAP: {imap_connection}")

    try:
        # IMAP 연결 확인
        if not imap_connection:
            print("IMAP connection is not established.")
            return jsonify({"status": "error", "message": "IMAP connection not established."})

        # 이메일 가져오기
        mails = imap_email_reader.read_email(imap_connection)
        if mails is None:
            print("Failed to read emails from IMAP.")
            return jsonify({"status": "error", "message": "Failed to read emails from IMAP."})

        # DB 연결
        conn = get_db_connection()
        if not conn:
            print("Database connection failed.")
            return jsonify({"status": "error", "message": "Database connection failed."}), 500

        new_mails = []

        # 이메일 저장 (중복 방지)
        for mail in reversed(mails):
            uid = mail.get('uid')
            existing_mail = conn.execute('SELECT id FROM emails WHERE uid = ?', (uid,)).fetchone()
            if not existing_mail:
                new_mails.append(mail)

        print(new_mails)

        # filtering
        filtered_mails = filter(new_mails)

        for mail in filtered_mails:
            insert_email(
                uid=mail.get('uid', 'No UID'),
                subject=mail.get('subject', 'No Subject'),
                sender=mail.get('sender', 'Unknown Sender'),
                sender_email=mail.get('sender_email', 'Unknown Email'),
                date=mail.get('date', 'Unknown Date'),
                body=mail.get('body', 'No Body'),
                html_body=mail.get('html_body', 'No HTML Body'),
                spam=mail.get('spam', 0)
            )
        conn.commit()
        conn.close()


        print("Emails successfully fetched and stored.")

    except Exception as e:
        print(f"Error during email fetching: {e}")

    print("Fetching 끝남...")
    return jsonify({"status": "success", "message": "Emails fetched and stored successfully."}), 200

@app.route("/api/filter", methods=["GET"])
def filter_emails():
    try:
        conn = get_db_connection()
    except Exception as e:
        print(f"Database connection failed: {e}")
        return jsonify({"status": "error", "message": "Database connection failed."}), 500

    try:
        # 'body'와 'html_body'를 제외하고 나머지 필드를 선택
        emails = conn.execute('''
                SELECT id, uid, subject, sender, sender_email, date, spam 
                FROM emails 
                WHERE spam = 0 
                ORDER BY id DESC
            ''').fetchall()

        if not emails:
            return jsonify({"status": "success", "emails": [], "message": "No emails found."}), 200

        # 결과를 딕셔너리로 변환
        emails_dict = [dict(email) for email in emails]
        print(emails_dict)

        return jsonify({"status": "success", "emails": emails_dict}), 200

    except Exception as e:
        print(f"Error fetching emails: {e}")
        return jsonify({"status": "error", "message": "Error fetching emails."}), 500
    finally:
        if conn:
            conn.close()

def filter(emails):
    for email in emails:
        combined_text = email['subject'] + " " + email['body']
        # combined_text = email['body']
        spam_prediction = predict_spam_email(combined_text)

        email['spam'] = int(spam_prediction) # 스팸 예측값을 이메일 정보에 추가
    return emails

def predict_spam_email(combined_text):
    email_vector = tfidf_vectorizer.transform([combined_text])

    prediction = model.predict(email_vector)

    return prediction[0]


"""클라이언트에게 공개키 전달"""
@app.route('/get_public_key', methods=['GET'])
def get_public_key():
    # 공개키를 PEM 형식으로 반환 (바이트 코드)
    return key_loader.load_public_key().export_key()

@app.route("/api/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        global server_name, decrypted_email, decrypted_password

        # POST로 받은 암호화된 email&pw - base64 인코딩 str
        encrypted_email = request.form['encrypted_email']
        encrypted_password = request.form['encrypted_password']
        service_provider = request.form['service_provider']

        # IMAP 서버 설정
        server_name = ""
        if service_provider == 'NAVER':
            server_name = 'imap.naver.com'
        elif service_provider == 'DAUM':
            server_name = 'imap.daum.net'
        elif service_provider == 'GMAIL':
            server_name = 'imap.gmail.com'

        # 복호화
        rsa = rsa_cipher.RSACipher()  # RSA 암복호화 객체
        try:
            decrypted_email = rsa.decrypt(encrypted_email)
            decrypted_password = rsa.decrypt(encrypted_password)
        except Exception as e:
            print(f"Decryption error: {e}")
            flash(f'복호화 오류: {str(e)}', 'error')
            return jsonify({'success': False, 'message': '복호화 오류 발생'})

        # 복호화 한 값을 imap 서버에 로그인
        # 로그인 시도해서 imap 객체를 반환받으면 성공, None 이면 실패
        if decrypted_email and decrypted_password:
            global imap_connection
            imap_connection = imap_email_reader.login_to_imap(server_name, decrypted_email, decrypted_password)
            if imap_connection:
                global user_email
                user_email = decrypted_email
                return redirect('/mailbox', code=301)
            else:
                # 로그인 실패
                login_fail = '로그인 실패: 아이디 또는 비밀번호가 틀렸습니다.'
                return render_template("login.html", login_fail=login_fail), 401

    else: # GET 요청 처리: 로그인 페이지 표시
        return render_template("login.html")


@app.route("/api/logout", methods=["POST"])
def logout():
    global imap_connection, user_email, server_name, decrypted_email, decrypted_password
    print(f"IMAP: {imap_connection}")
    imap_email_reader.logout_imap(imap_connection)
    imap_connection = None
    user_email = None
    server_name = decrypted_email = decrypted_password = None
    return jsonify({"status": "success", "message": "Logged out successfully."}), 200

if __name__ == '__main__':
    create_table()
    app.run(debug=True)