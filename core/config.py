import os
from functools import lru_cache
from pathlib import Path
from typing import List, Union, Optional

from pydantic import IPvAnyAddress

from pydantic.v1 import BaseSettings


class Settings(BaseSettings):
    DEBUG: bool = True
    # SECRET_KEY 记得保密生产环境 不要直接写在代码里面
    SECRET_KEY: str = '(-ASp+_)-Ulhw0848hnvVG-iqKyJSD&*&^-H3C9mqEqSl8KN-YRzRE'

    # jwt加密算法
    JWT_ALGORITHM: str = 'HS256'
    # jwt token过期时间 60 minutes * 24 hours * 8 days = 8 days
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 8

    # 跨域
    BACKEND_CORS_ORIGINS: List[str] = ['*']

    # mysql 配置
    MYSQL_USERNAME: str = 'root'
    MYSQL_PASSWORD: str = '123456'
    MYSQL_HOST: Union[IPvAnyAddress, str] = '127.0.0.1'
    MYSQL_DATABASE: str = 'innoverse'

    # mysql地址
    SQLALCHEMY_DATABASE_URI = f'mysql+aiomysql://{MYSQL_USERNAME}:{MYSQL_PASSWORD}@{MYSQL_HOST}/{MYSQL_DATABASE}?charset=utf8mb4'
    SQLALCHEMY_ECHO = True

    # redis配置
    REDIS_HOST: str = '127.0.0.1'
    REDIS_PASSWORD: str = ""
    REDIS_DB: int = 0
    REDIS_PORT: int = 6379
    REDIS_URL: str = f'redis://:{REDIS_PASSWORD}@{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}?encoding=utf-8'

    class Config:
        # 区分大小写
        case_sensitive = True
        # 设置需要识别的 .env 文件
        env_file = '.env'
        # 设置字符编码
        env_file_encoding = 'utf-8'


@lru_cache()
def get_setting():
    # 更加环境变量读取配置
    env_var = str.lower(os.getenv('FAST_API_ENV', 'dev'))
    if env_var not in ['dev', 'prod', 'test']:
        raise Exception(f'invalid env var: {env_var}')
    env_file_path = Path(__file__).parent.joinpath('env').joinpath(f'.env_{env_var}').as_posix()
    return Settings(_env_file=env_file_path, _env_file_encoding='utf-8')


setting = get_setting()
