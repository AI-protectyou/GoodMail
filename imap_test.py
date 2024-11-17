import csv
import imaplib
import email
from email.header import decode_header
from bs4 import BeautifulSoup
import re

"""HTML 콘텐츠에서 텍스트를 추출하는 함수"""


def extract_text_from_html(html_content):
    if not isinstance(html_content, str) or not html_content.strip():
        return "유효하지 않은 HTML 콘텐츠"  # 입력이 문자열이 아니거나 비어있을 경우 처리

    try:
        # HTML 콘텐츠가 유효한지 확인
        if not html_content.startswith('<'):
            html_content = f"<html><body>{html_content}</body></html>"  # 기본적인 HTML 태그 추가

        soup = BeautifulSoup(html_content, "html.parser")
    except Exception as e:
        return f"HTML 파싱 오류: {str(e)}"  # 구체적인 오류 메시지 반환

    texts = soup.stripped_strings  # 모든 텍스트 추출
    full_text = ' '.join(texts)  # 추출된 텍스트를 하나의 문자열로 결합

    # 본문에서 개행 문자 및 불필요한 공백 제거하기
    cleaned_text = full_text.strip()
    cleaned_text = cleaned_text.replace('\n', ' ').replace('\r', ' ')
    cleaned_text = re.sub(r'\s+', ' ', cleaned_text)  # 여러 개의 공백을 하나로

    return cleaned_text


"""인코딩된 MIME 문자열을 디코딩하는 함수 - subject, from_"""


def decode_mime_words(s):
    if s is None:  # None 체크 추가
        return ""  # None인 경우 빈 문자열 반환

    decoded_string = ''
    for word, encoding in decode_header(s):
        if isinstance(word, bytes):
            if encoding is None or encoding.lower() == 'unknown-8bit':
                encoding = 'utf-8'
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
    encoding_list = ["utf-8", "euc-kr", "iso-8859-1"]

    # 메시지가 다중 파트인지 확인
    if msg.is_multipart():
        for part in msg.walk():
            content_type = part.get_content_type()

            # 일반 텍스트가 있는 경우 우선적으로 가져옴
            if content_type == "text/plain" or (content_type == "text/html" and not body):
                body = decode_payload(part, encoding_list)
                if body:
                    break  # 본문을 성공적으로 디코딩한 경우 종료
    else:
        # 단일 파트 메시지일 때
        body = decode_payload(msg, encoding_list)

    return body


"""본문을 디코딩하는 함수"""


def decode_payload(part, encodings):
    payload = part.get_payload(decode=True)
    for encoding in encodings:
        try:
            return payload.decode(encoding)
        except UnicodeDecodeError:
            continue
    return ""  # 디코딩 실패 시 빈 문자열 반환


"""IMAP 서버에 로그인, 연결 객체(imap) 반환"""


def login_to_imap(imap_server, username, password):
    try:
        imap = imaplib.IMAP4_SSL(imap_server, port=993)
        status, response = imap.login(username, password)
        if status == 'OK':
            return imap  # IMAP 연결 객체 반환
        else:
            return None
    except imaplib.IMAP4.error as e:
        return None


"""로그아웃"""


def logout_imap(imap):
    imap.close()
    imap.logout()


"""이메일 주소를 포함하는 이름과 이메일을 분리하는 정규식"""


def extract_sender_name_and_email(from_field):
    match = re.match(r'"?([^"]+)"?\s?<?([^>]+)>?', from_field)
    if match:
        name = match.group(1)  # 이름
        email = match.group(2)  # 이메일 주소
        return name, email
    else:
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
        # UID를 바이트 문자열로 변환하여 fetch 호출
        uid_to_fetch = str(12777).encode('utf-8')  # UID를 바이트 문자열로 변환

        #status, data = imap.uid('search', None, 'ALL')
        status, msg_data = imap.uid('fetch', uid_to_fetch, '(RFC822)')
        if status != 'OK':
            raise Exception("이메일 검색 실패")


        response_part = msg_data[0]
        if isinstance(response_part, tuple):
            email_body = response_part[1]
            email_message = email.message_from_bytes(email_body)

            # 이메일의 제목, 발신자, 날짜를 가져옴
            subject = decode_mime_words(email_message["Subject"])
            from_ = decode_mime_words(email_message["From"])
            sender, sender_email = extract_sender_name_and_email(from_)
            date = email_message["Date"]

            # 본문 내용 가져옴
            body_content = ""
            body = get_email_body(email_message)
            if body.strip():
                body_content = extract_text_from_html(body)

            # 이메일 정보를 딕셔너리 형태로 추가
            emails.append({
                "subject": subject,
                "sender": sender,
                "sender_email": sender_email,
                "date": date,
                "body": body_content
            })

            print(emails)

    except imaplib.IMAP4.error as e:
        print(f"로그인 실패: {e}")
    except Exception as e:
        print(f"오류 발생: {e}")

    return emails  # 이메일 리스트 정보 반환


def save_emails_to_csv(emails, filename='emails.csv'):
    """이메일 정보를 CSV 파일로 저장하는 함수"""
    with open(filename, mode='w', newline='', encoding='utf-8') as csvfile:
        fieldnames = ["uid", "subject", "sender", "sender_email", "date", "body"]
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

        writer.writeheader()  # 헤더 작성

        for email in emails:
            writer.writerow(email)  # 각 이메일 정보 작성


if __name__ == "__main__":
    imap_server = "imap.naver.com"  # 예시: Naver IMAP 서버 주소
    username = ""  # 이메일 주소 입력
    password = ""  # 비밀번호 입력

    # IMAP 서버에 로그인
    imap_connection = login_to_imap(imap_server, username, password)

    if imap_connection:
        print("로그인 성공! 이메일을 불러오는 중...")

        # 이메일 목록 읽기
        emails = read_email(imap_connection)  # err

        # 이메일 목록 출력
        print(f"총 {len(emails)}개의 이메일을 읽었습니다.")

        # CSV 파일로 저장
        #save_emails_to_csv(emails)
        #print("이메일 정보를 CSV 파일로 저장했습니다.")

        # 연결 종료
        logout_imap(imap_connection)

    else:
        print("로그인 실패!")