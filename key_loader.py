import os
from dotenv import load_dotenv
from Crypto.PublicKey import RSA

# .env 파일 로드
load_dotenv()

# PUBLIC_KEY 가져오기
def load_public_key():
    public_key_pem = os.getenv("PUBLIC_KEY")

    if public_key_pem is None:
        raise ValueError("PUBLIC_KEY 환경변수에 값이 없습니다.")

    try:
        public_key = RSA.import_key(public_key_pem)
        #print("Public key loaded successfully.")
        return public_key
    except ValueError as e:
        print(f"Error loading public key: {e}")
        raise
    except Exception as e:
        print(f"Unexpected error: {e}")
        raise

# PRIVATE_KEY 가져오기
def load_private_key():
    private_key_pem = os.getenv("PRIVATE_KEY")

    if private_key_pem is None:
        raise ValueError("PRIVATE_KEY 환경변수에 값이 없습니다.")

    try:
        RSA.import_key(private_key_pem)
        private_key = RSA.import_key(private_key_pem)
        #print("Private key loaded successfully.")
        return private_key
    except ValueError as e:
        print(f"Error loading private key: {e}")
        raise
    except Exception as e:
        print(f"Unexpected error: {e}")
        raise