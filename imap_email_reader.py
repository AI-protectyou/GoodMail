import imaplib
import email
from email.header import decode_header
from bs4 import BeautifulSoup
import re
import chardet
def extract_text_from_html(html_content):
    if html_content:
        if isinstance(html_content, bytes):
            print(f"html_content 타입: {type(html_content)}")
            html_content = html_content.decode('utf-8', errors='ignore')
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            texts = soup.stripped_strings
            full_text = ' '.join(texts)
            return re.sub(r'\s+', ' ', full_text).strip()
        except Exception as e:
            print(f"HTML 파싱 오류: {e}")
            return html_content  # 오류가 발생할 경우 원본 반환
    return ""


def decode_mime_words(s):
    if not s:
        return ""
    decoded_string = ''
    for word, encoding in decode_header(s):
        if isinstance(word, bytes):
            encoding = encoding or 'utf-8'
            try:
                decoded_string += word.decode(encoding)
            except (UnicodeDecodeError, LookupError) as e:
                print(f"디코딩 오류: {s} (encoding: {encoding}, error: {e})")
                # 더 많은 인코딩 시도
                try:
                    decoded_string += word.decode('utf-8', errors='replace')
                except UnicodeDecodeError:
                    decoded_string += word.decode('iso-8859-1', errors='replace')
        else:
            decoded_string += word
    return decoded_string

def decode_payload(part):
    payload = part.get_payload(decode=True)
    if payload is not None:
        for encoding in ['utf-8', 'iso-8859-1', 'euc-kr', 'cp949', 'utf-16', 'utf-32']:
            try:
                return payload.decode(encoding)
            except (UnicodeDecodeError, LookupError):
                continue
        print("모든 디코딩 시도 실패, 원시 데이터 반환")
        return payload.decode('utf-8', errors='replace')  # 기본적으로 utf-8로 반환
    return ""


def get_email_body(msg):
    body = ""
    if msg.is_multipart():
        for part in msg.walk():
            content_type = part.get_content_type()
            content_disposition = str(part.get("Content-Disposition"))

            if 'attachment' not in content_disposition:
                if content_type == "text/plain" or content_type == "text/html":
                    body = decode_payload(part)
                    if body:
                        break
    else:
        body = decode_payload(msg)
    return body


def login_to_imap(imap_server, username, password):
    try:
        imap = imaplib.IMAP4_SSL(imap_server, port=993, timeout=60)
        status, response = imap.login(username, password)
        if status == 'OK':
            return imap
        else:
            print(f"IMAP 로그인 실패: {response}")
            return None
    except imaplib.IMAP4.error as e:
        print(f"IMAP 로그인 오류: {e}")
        return None
    except Exception as e:
        print(f"오류 : {e}")
        return None


def logout_imap(imap):
    try:
        imap.logout()
        print("로그아웃 성공")
    except Exception as e:
        print(f"로그아웃 오류: {str(e)}")


def extract_sender_name_and_email(from_field):
    match = re.match(r'^(.*?)(?:\s*<([^>]+)>)?$', from_field.strip())
    if match:
        name = match.group(1).strip().strip('"')
        email = match.group(2)
        return name, email
    return from_field, None


def read_email(imap):
    emails = []
    try:
        imap.select('INBOX')
        status, data = imap.uid('search', None, 'ALL')
        if status != 'OK':
            raise Exception("이메일 검색 실패")
        email_uids = data[0].split()
        print(f'이메일 길이: {len(email_uids)}')

        recent_email_uids = email_uids[-50:]  # 최근 100개 이메일만 선택

        for email_uid in reversed(recent_email_uids):
            _, msg_data = imap.uid('fetch', email_uid, '(RFC822)')
            response_part = msg_data[0]
            if isinstance(response_part, tuple):
                email_body = response_part[1]
                email_message = email.message_from_bytes(email_body)

                subject = decode_mime_words(email_message["Subject"])
                from_ = decode_mime_words(email_message["From"])
                sender, sender_email = extract_sender_name_and_email(from_)
                date = email_message["Date"]
                html_content = get_email_body(email_message)
                body_content = ""
                if html_content.strip():
                    body_content = extract_text_from_html(html_content)

                emails.append({
                    "uid": email_uid.decode(),
                    "subject": subject,
                    "sender": sender,
                    "sender_email": sender_email,
                    "date": date,
                    "body": body_content,
                    "html_body": html_content
                })


    except (imaplib.IMAP4.error, Exception) as e:
        print(f"이메일 읽기 오류: {e}")

    return emails


"""# 테스트 실행 부분 (예: main 함수 안에서)
if __name__ == "__main__":
    imap_server = "imap.naver.com"
    username = ""
    password = ""  # 비밀번호는 보안상 코드에 하드코딩하지 마세요!

    imap_connection = login_to_imap(imap_server, username, password)

    if imap_connection:
        print("로그인 성공! 이메일을 불러오는 중...")
        emails = read_email(imap_connection)
        print(f"총 {len(emails)}개의 이메일을 읽었습니다.")
        for email in emails:
            print(f'uid: {email["uid"]}')
            print(f'subject: {email["subject"]}')
            print(f'sender: {email["sender"]}')
            print(f'sender_email: {email["sender_email"]}')
            print(f'date: {email["date"]}')
            print(f'body: {email["body"]}')
            print('*' * 50)
        logout_imap(imap_connection)
    else:
        print("로그인 실패!")"""