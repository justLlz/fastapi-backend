from datetime import timedelta, timezone, datetime
from typing import Optional

import jwt
from loguru import logger

from internal.setting import setting


async def verify_jwt_token(token: str) -> (Optional[int], bool):
    """
    验证 Token = request.headers.get("Authorization")
    """
    if not token or not token.startswith("Bearer "):
        return False

    token = token.split(" ")[1]
    try:
        payload = jwt.decode(token, setting.SECRET_KEY, algorithms=[setting.JWT_ALGORITHM])
        user_id = payload.get("user_id")
        if user_id is None:
            logger.warning("Token verification failed: user_id not found")
            return None, False
    except jwt.ExpiredSignatureError:
        logger.warning("Token verification failed: token expired")
        return None, False
    except jwt.InvalidTokenError:
        logger.warning("Token verification failed: invalid token")
        return None, False

    return user_id, True


def create_jwt_token(user_id: int, username: str):
    expiration = datetime.now(timezone.utc) + timedelta(minutes=setting.ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {
        "username": username,
        "user_id": user_id,
        "exp": int(expiration.timestamp())  # Token 有效期 30 分钟
    }
    return jwt.encode(payload, setting.SECRET_KEY, algorithm=setting.JWT_ALGORITHM)
