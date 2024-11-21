import os

import tensorflow
from flask import Flask,jsonify, render_template, url_for, request, redirect, session, flash
from dotenv import load_dotenv
from datetime import timedelta
import imap_email_reader
import key_loader
import rsa_cipher
import sqlite3
import ssl
import tensorflow.keras.models
from sklearn.feature_extraction.text import TfidfVectorizer
from tensorflow.keras.preprocessing.text import Tokenizer
from tensorflow.keras.preprocessing.sequence import pad_sequences

loaded_model = tensorflow.keras.models.load_model('spam_model.h5')
app = Flask(__name__)

# 모델 로드
#loaded_model = joblib.load('model.pkl')

# Flask 앱에 secret_key 설정 (세션 암호화용)
app.secret_key = os.getenv('SECRET_KEY', 'your_default_secret_key')  # .env 파일에서 비밀 키를 가져오거나 기본값을 사용

imap_connection = None
vectorizer = TfidfVectorizer()  # 벡터화 도구를 전역으로 선언
@app.route("/")
def home():
    return render_template("login.html")

"""메일 리스트"""
@app.route("/mailbox")
def mailbox():
    return render_template("mail_list.html")

@app.route("/api/get_mail")
def get_mail():
    global imap_connection
    mails = imap_email_reader.read_email(imap_connection)
    print(mails)

    new_mails = filter(mails)
    return jsonify(new_mails)

# ai 코드
def filter_emails(mails):
    filtered_emails = []
    for email in mails:
        if 'Steam' not in email.get('subject', ''):
            filtered_emails.append(email)
        else:
            print(f"Removed email: {email}")
    return filtered_emails


def filter(mails):
    filtered_emails = []
    tokenizer = Tokenizer()

    """email_texts = [
        email.get('subject', '') + " " + email.get('sender', '') + " " + email.get('sender_email', '') + " " + email.get('date', '') + " " + email.get('body', '')
        for email in mails
    ]"""

    for email in mails:
        email_texts = [
            email.get('body', '') for email in mails
        ]

        email_text_encoded = tokenizer.texts_to_sequences([email_texts])

        email_text_padded = pad_sequences(email_text_encoded, maxlen=189)

        prediction = loaded_model.predict(email_text_padded)
        print(f"Prediction: {prediction}")  # 예측값 확인

        if prediction[0][0] < 0.2:
            filtered_emails.append(email)
        else:
            print(f"Removed spam email: {email}")

    """for email in mails:
        subject = email.get('subject', '')
        sender = email.get('sender', '')
        sender_email = email.get('sender_email', '')
        date = email.get('date', '')
        body = email.get('body', '')
        email_text = subject + " " + sender + " " + sender_email + " " + date + " " + body

        email_text_vector = vectorizer.transform([email_text])

        prediction = loaded_model.predict(email_text_vector)
        print(f"Prediction: {prediction}")  # 예측값 확인

        if prediction[0][0] < 0.5:  # 0.5 기준으로 분류
            filtered_emails.append(email)
        else:
            print(f"Removed spam email: {email}")"""
    print(f'filtered_emails len = {len(filtered_emails)}')
    return filtered_emails

@app.route("/mail/<int:mail_id>")
def mail(mail_id):
    # db 에서 메일 가져오기
    return render_template("mail_content.html")

"""클라이언트에게 공개키 전달"""
@app.route('/get_public_key', methods=['GET'])
def get_public_key():
    # 공개키를 PEM 형식으로 반환 (바이트 코드)
    return key_loader.load_public_key().export_key()

@app.route("/login", methods=["GET", "POST"])
def login(): #
    if request.method == "POST":
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
            if imap_connection:  # 로그인 성공
                print("imap 로그인 성공!!")
                #imap_connection.logout() # 일단 test 하려고 로그인만 확인하고 연결 끊기
                # 이메일 목록 페이지로 리디렉션
                return redirect(url_for('mailbox'))

            else:
                # 로그인 실패
                login_fail = '로그인 실패: 아이디 또는 비밀번호가 틀렸습니다.'
                return render_template("login.html", login_fail=login_fail), 401

    else: # GET 요청 처리: 로그인 페이지 표시
        login_fail = '이메일 또는 비밀번호가 제공되지 않았습니다.'
        return render_template("login.html", login_fail=login_fail), 400


if __name__ == '__main__':
    app.run(debug=True)