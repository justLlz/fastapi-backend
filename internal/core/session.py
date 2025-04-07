from typing import Optional

from pkg import session_list_cache_key
from internal.utils.cache_helpers import Cache
from pkg.logger_helper import logger


async def verify_session(session: str) -> (Optional[dict], bool):
    if not session:
        logger.warning("Token verification failed: token not found")
        return None, False

    user_data: dict = await Cache.get_session_value(session)
    if user_data is None:
        logger.warning("Token verification failed: session not found")
        return None, False

    user_id = user_data.get("id")
    # 检查有没有在session 列表里
    session_list = await Cache.get_list(session_list_cache_key(user_id))
    if session_list is None or session not in session_list:
        logger.warning(f"Token verification failed: session not found in session list, user_id: {user_id}")
        return None, False

    return user_data, True
