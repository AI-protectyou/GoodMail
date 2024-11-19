from Crypto.PublicKey import RSA
from Crypto.Cipher import PKCS1_OAEP
from Crypto.Random import get_random_bytes

# 2048 비트 RSA 키 쌍 생성
key = RSA.generate(2048, get_random_bytes)

# 공개키와 개인키를 PEM 형식으로 저장
private_key_pem = key.export_key()
public_key_pem = key.publickey().export_key()

# 개인키와 공개키를 문자열로 변환하여 출력
print("Private Key:")
print(private_key_pem.decode('utf-8'))  # 개인키 출력

print("\nPublic Key:")
print(public_key_pem.decode('utf-8'))  # 공개키 출력