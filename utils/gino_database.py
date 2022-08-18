from gino import Gino, GinoEngine, GinoConnection

from settings import setting

db = await Gino(
    pool_min_size=setting.DB_POOL_MIN_SIZE,
    pool_max_size=setting.DB_POOL_MAX_SIZE,
    echo=setting.DB_ECHO,
    ssl=setting.DB_SSL,
    use_connection_for_request=setting.DB_USE_CONNECTION_FOR_REQUEST,
    retry_limit=setting.DB_RETRY_LIMIT,
    retry_interval=setting.DB_RETRY_INTERVAL,
)
