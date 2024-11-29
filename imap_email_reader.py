import imaplib
import email
from email.header import decode_header
from bs4 import BeautifulSoup
import re

"""HTML 콘텐츠에서 텍스트를 추출하는 함수"""
def extract_text_from_html(html_content):
    try:
        soup = BeautifulSoup(html_content, 'html.parser')
        texts = soup.stripped_strings
        full_text = ' '.join(texts)  # 텍스트 결합
        cleaned_text = full_text.strip().replace('\n', ' ').replace('\r', ' ')
        return re.sub(r'\s+', ' ', cleaned_text)
    except Exception as e:
        return f"HTML 파싱 오류: {str(e)}"


"""인코딩된 MIME 문자열을 디코딩하는 함수 - subject, from_"""
def decode_mime_words(s):
    if not s:
        return ""
    decoded_string = ''
    for word, encoding in decode_header(s):
        if isinstance(word, bytes):
            encoding = encoding or 'utf-8'
            try:
                decoded_string += word.decode(encoding)
            except (LookupError, UnicodeDecodeError):
                decoded_string += word.decode('utf-8', errors='replace')
        else:
            decoded_string += word
    return decoded_string


"""이메일 메시지에서 본문 내용을 추출하는 함수"""
def get_email_body(msg):
    body = ""
    # 메시지가 다중 파트인지 확인
    if msg.is_multipart():
        for part in msg.walk():
            content_type = part.get_content_type()

            # HTML 본문이 있는 경우 가져옴
            if content_type == "text/html":
                body = decode_payload(part)
                break  # HTML 본문을 찾으면 종료
            elif content_type == "text/plain":
                body = decode_payload(part)  # 일반 텍스트도 가져올 수 있음
    else:
        body = decode_payload(msg) # 단일 파트 메시지일 때

    return body


def decode_payload(part):
    payload = part.get_payload(decode=True)
    try:
        return payload.decode('utf-8', errors='replace')  # UTF-8로 디코딩
    except UnicodeDecodeError:
        # UTF-8로 디코딩 실패 시, 다른 인코딩 시도
        return payload.decode('iso-8859-1', errors='replace')  # ISO-8859-1로 디코딩


"""IMAP 서버에 로그인, 연결 객체(imap) 반환"""
def login_to_imap(imap_server, username, password):
    try:
        imap = imaplib.IMAP4_SSL(imap_server, port=993)
        status, response = imap.login(username, password)
        if status == 'OK':
            return imap  # IMAP 연결 객체 반환
        else:
            print(f"IMAP 로그인 실패: {response}")
            return None
    except imaplib.IMAP4.error as e:
        return None


"""로그아웃"""
def logout_imap(imap):
    try:
        imap.logout()
    except Exception as e:
        print(f"로그아웃 오류: {str(e)}")


"""이메일 주소를 포함하는 이름과 이메일을 분리하는 정규식"""
def extract_sender_name_and_email(from_field):
    match = re.match(r'^(.*?)(?:\s*<([^>]+)>)?$', from_field.strip())
    if match:
        name = match.group(1).strip().strip('"')  # 이름
        email = match.group(2)  # 이메일 주소 (꺾쇠 괄호 안)
        return name, email
    return from_field, None  # 이름과 이메일이 없을 경우


"""
    * 메일의 제목, 발신자, 날짜, 본문 가져오는 함수
    * 반환 타입 : 'dictionary 객체'
    UID : email_uid.decode() # str type
    제목 : subject            # str type
    날짜 : from_              # str type
    날짜 : date               # str type
    본문 : body_content       # str type
    
    "INBOX"                         -> 받은 편지함
    "Sent Messages"                 -> 보낸 편지함
    "Drafts"                        -> 임시 저장된 편지함
    Trash "Deleted Messages"        -> 삭제된 메일이 저장되는 폴더 like Trash
    Junk "Junk"                     -> 스팸 메일이 자동으로 분류되어 저장되는 폴더
    "&sLSsjMT0ulTHfNVo-"           
    "&zK2tbAC3rLDIHA-"
    "SNS"                            -> 소셜 네트워크 서비스와 관련된 메일을 받는 폴더
    "&1QS4XLqowVg-"
"""
def read_email(imap):
    emails = []  # 이메일 정보를 담을 리스트
    # 이메일 읽기 로직
    try:
        imap.select('INBOX')
        status, data = imap.uid('search', None, 'ALL')
        if status != 'OK':
            raise Exception("이메일 검색 실패")

        email_uids = data[0].split()
        email_len = len(email_uids)
        print(f'email length : {email_len}')

        # 최근 n개의 이메일 UID만 선택
        recent_email_uids = email_uids[-100:]  # 마지막 n개 UID 선택

        for email_uid in reversed(recent_email_uids):
            _, msg_data = imap.uid('fetch', email_uid, '(RFC822)')
            response_part = msg_data[0]
            if isinstance(response_part, tuple):
                email_body = response_part[1]
                email_message = email.message_from_bytes(email_body)

                # 이메일의 제목, 발신자, 날짜를 가져옴
                subject = decode_mime_words(email_message["Subject"])
                from_ = decode_mime_words(email_message["From"])
                sender, sender_email = extract_sender_name_and_email(from_)
                date = email_message["Date"]
                body_content = get_email_body(email_message) # 본문 내용 가져옴 (HTML 형식으로)

                if body_content.strip():
                    body_content = extract_text_from_html(body_content)

                # 이메일 정보를 딕셔너리 형태로 추가
                emails.append({
                    "uid": email_uid.decode(),
                    "subject": subject,
                    "sender": sender,
                    "sender_email": sender_email,
                    "date": date,
                    "body": body_content
                })

        imap.close()

    except imaplib.IMAP4.error as e:
        print(f"이메일 읽기 오류: {e}")

    return emails  # 이메일 리스트 정보 반환

"""
if __name__ == "__main__":
    imap_server = "imap.naver.com"  # 예시: Naver IMAP 서버 주소
    username = "tjguswn02@naver.com"  # 이메일 주소 입력
    password = ""  # 비밀번호 입력

    # IMAP 서버에 로그인
    imap_connection = login_to_imap(imap_server, username, password)

    if imap_connection:
        print("로그인 성공! 이메일을 불러오는 중...")

        # 이메일 목록 읽기
        emails = read_email(imap_connection) # err

        # 이메일 목록 출력
        print(f"총 {len(emails)}개의 이메일을 읽었습니다.")

        for email in emails:
            print(f'uid : {email["uid"]} (type: {type(email["uid"]).__name__})')
            print(f'subject : {email["subject"]} (type: {type(email["subject"]).__name__})')
            print(f'sender : {email["sender"]} (type: {type(email["sender"]).__name__})')
            print(f'sender_email : {email["sender_email"]} (type: {type(email["sender_email"]).__name__})')
            print(f'date : {email["date"]} (type: {type(email["date"]).__name__})')
            print(f'body : {email["body"]} (type: {type(email["body"]).__name__})')
            print('*' * 50)

        # CSV 파일로 저장
        #save_emails_to_csv(emails)
        #print("이메일 정보를 CSV 파일로 저장했습니다.")

        # 연결 종료
        logout_imap(imap_connection)

    else:
        print("로그인 실패!")
"""