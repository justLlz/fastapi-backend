import jwt
from datetime import datetime, timedelta, timezone

from config import setting


def create_access_token(user_id: int, user_name: str):
    expiration = datetime.now(timezone.utc) + timedelta(minutes=setting.ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {
        "user_name": user_name,
        "user_id": user_id,
        "exp": int(expiration.timestamp())  # Token 有效期 30 分钟
    }
    return jwt.encode(payload, setting.SECRET_KEY, algorithm=setting.JWT_ALGORITHM)
