import jwt
from datetime import datetime, timedelta, timezone

from config import setting


def create_token(user_id: int, user_name: str):
    expiration = datetime.now(timezone.utc) + timedelta(minutes=3000)
    payload = {
        "user_name": user_name,
        "user_id": user_id,
        "exp": int(expiration.timestamp())  # Token 有效期 30 分钟
    }
    return jwt.encode(payload, setting.SECRET_KEY, algorithm=setting.ALGORITHM)


if __name__ == '__main__':
    token = create_token(user_id=7256870410837295104, user_name="root")
    print(token)
