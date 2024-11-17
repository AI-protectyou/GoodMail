import sqlite3

conn = sqlite3.connect("test.db")
cursor = conn.cursor()

# 테이블 생성
sql_command="""
CREATE TABLE IF NOT EXISTS emails (
    uid INTEGER PRIMARY KEY,
    subject TEXT,
    sender TEXT,
    sender_email TEXT,
    date TEXT
)
"""
# 테이블 생성
cursor.execute(sql_command)

# 예시 데이터 삽입 (테스트용)
cursor.execute("INSERT INTO emails")
cursor.execute("INSERT INTO emails")

# 메일 정보
uid = 24198
subject = "Steam 계정 복구"
sender = "Steam Support"
sender_email = "noreply@steampowered.com"
date = "Fri, 15 Nov 2024 02:23:44 -0800"

# INSERT 쿼리 실행
cursor.execute("""
INSERT INTO emails (uid, subject, sender, sender_email, date) 
VALUES (?, ?, ?, ?, ?)
""", (uid, subject, sender, sender_email, date))


# 결과 가져오기
results = cursor.fetchall()  # 모든 결과를 가져옴

# 결과 출력
for row in results:
    print(row)

# 체인지 커밋
conn.commit()
conn.close()