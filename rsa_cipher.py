from Crypto.PublicKey import RSA
from Crypto.Cipher import PKCS1_OAEP
from Crypto.Cipher import PKCS1_v1_5
import base64
import key_loader

class RSACipher:
    def __init__(self):
        self.public_key = key_loader.load_public_key()
        self.private_key = key_loader.load_private_key()
        self.encrypt_cipher = PKCS1_v1_5.new(self.public_key)  # PKCS1 v1.5 패딩
        self.decrypt_cipher = PKCS1_v1_5.new(self.private_key)

    def encrypt(self, plaintext: str) -> str:
        encrypted_bytes = self.encrypt_cipher.encrypt(plaintext.encode()) # str.encode() : 문자열을 바이트로 변환
        return base64.b64encode(encrypted_bytes).decode('utf-8')


    def decrypt(self, encrypted_base64: str) -> str:
        encrypted_bytes = base64.b64decode(encrypted_base64)
        decrypted_bytes = self.decrypt_cipher.decrypt(encrypted_bytes, None)  # 두 번째 인자는 None으로 설정
        if decrypted_bytes is None:
            raise ValueError("Decryption failed.")
        return decrypted_bytes.decode('utf-8') # bytes.decode() : 바이트를 문자열로 변환