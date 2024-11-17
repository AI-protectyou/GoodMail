import os
from flask import Flask,jsonify, render_template, url_for, request, redirect, session, flash
from dotenv import load_dotenv
from datetime import timedelta
import imap_email_reader
import key_loader
import rsa_cipher
import sqlite3

app = Flask(__name__)

# 모델 로드
#loaded_model = joblib.load('model.pkl')

# Flask 앱에 secret_key 설정 (세션 암호화용)
app.secret_key = os.getenv('SECRET_KEY', 'your_default_secret_key')  # .env 파일에서 비밀 키를 가져오거나 기본값을 사용

"""# 세션 및 연결 관리 변수
imap_connection = None
last_login_time = None"""
@app.route("/")
def home():
    return render_template("login.html")

"""1. 메일 보여주기 버튼, 2. 인공지능 분석 버튼"""
@app.route("/mailbox")
def mailbox():
    emails = session.get('emails', [])
    return render_template("mail_list.html", emails=emails)

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
def login():
    if request.method == "POST":
        # POST로 받은 암호화된 email&pw - base64 인코딩 str
        encrypted_email = request.form['encrypted_email']
        encrypted_password = request.form['encrypted_password']
        service_provider = request.form['service_provider']

        # IMAP 서버 설정
        server_name = ""
        if service_provider == 'naver':
            server_name = 'imap.naver.com'
        elif service_provider == 'daum':
            server_name = 'imap.daum.net'
        elif service_provider == 'gmail':
            server_name = 'imap.gmail.com'

        # 복호화
        rsa = rsa_cipher.RSACipher()  # RSA 암복호화 객체
        try:
            decrypted_email = rsa.decrypt(encrypted_email)
            decrypted_password = rsa.decrypt(encrypted_password)
            print(f"Decrypted email: {decrypted_email}")
            print(f"Decrypted password: {decrypted_password}")
        except Exception as e:
            print(f"Decryption error: {e}")
            flash(f'복호화 오류: {str(e)}', 'error')
            return jsonify({'success': False, 'message': '복호화 오류 발생'})

        login_successful = False
        if decrypted_email and decrypted_password:
            if decrypted_email == 'tjguswn02@naver.com' and decrypted_password == '1234':
                login_successful = True
        if login_successful:
            return redirect(url_for('mailbox'))
        else:
            return jsonify({'success': False, 'message': '로그인 실패'})

        # 복호화 한 값을 imap 서버에 로그인
        """# 로그인 시도해서 imap 객체를 반환받으면 성공, None 이면 실패
        if decrypted_email and decrypted_password:
            imap_connection = imap_email_reader.login_to_imap(service_provider, decrypted_email, decrypted_password)
            if imap_connection:  # 로그인 성공
                print("imap 로그인 성공!!")

                # 세션에 암호화된 이메일과 비밀번호, 서버 저장
                session['encrypted_email'] = encrypted_email
                session['encrypted_password'] = encrypted_password
                session['server_name'] = server_name

                # 이메일 목록 페이지로 리디렉션
                return redirect(url_for('mailbox'))

            else:
                # 로그인 실패
                login_fail = '로그인 실패 : 아이디 또는 비밀번호가 틀렸습니다.'
                return render_template("logining.html", login_fail=login_fail)"""

    else: # GET 요청 처리: 로그인 페이지 표시
        return render_template("logining.html")


if __name__ == '__main__':
    app.run(debug=True)