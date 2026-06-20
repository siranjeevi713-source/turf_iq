import jwt
import os
import datetime

JWT_SECRET = os.environ.get("JWT_SECRET", "super-secret-key-for-turffiq")
JWT_ALGORITHM = "HS256"

def sign_jwt(user_id: str, role: str):
    payload = {
        "user_id": user_id,
        "role": role,
        "exp": datetime.datetime.utcnow() + datetime.timedelta(days=7)
    }
    encoded_jwt = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
    return encoded_jwt

def decode_jwt(token: str):
    try:
        decoded_token = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return decoded_token
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None
