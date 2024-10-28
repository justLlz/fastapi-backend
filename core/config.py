from functools import lru_cache
from pathlib import Path
from typing import List, Union
from pydantic import IPvAnyAddress
from pydantic.v1 import BaseSettings

from utils import get_env_var


class BaseConfig(BaseSettings):
    DEBUG: bool = True
    SECRET_KEY: str = '(-ASp+_)-Ulhw0848hnvVG-iqKyJSD&*&^-H3C9mqEqSl8KN-YRzRE'

    # JWT 配置
    JWT_ALGORITHM: str = 'HS256'
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 8  # 8 天

    # CORS 配置
    BACKEND_CORS_ORIGINS: List[str] = ['*']

    # MySQL 配置
    MYSQL_USERNAME: str = 'root'
    MYSQL_PASSWORD: str = '123456'
    MYSQL_HOST: Union[IPvAnyAddress, str] = '127.0.0.1'
    MYSQL_DATABASE: str = 'innoverse'

    # Redis 配置
    REDIS_HOST: str = '127.0.0.1'
    REDIS_PASSWORD: str = ''
    REDIS_DB: int = 0
    REDIS_PORT: int = 6379

    class Config:
        case_sensitive = True
        env_file_encoding = 'utf-8'

    @property
    def sqlalchemy_database_uri(self) -> str:
        return f'mysql+aiomysql://{self.MYSQL_USERNAME}:{self.MYSQL_PASSWORD}@{self.MYSQL_HOST}/{self.MYSQL_DATABASE}?charset=utf8mb4'

    @property
    def sqlalchemy_echo(self) -> bool:
        return self.DEBUG  # 开发环境启用 SQLAlchemy 日志

    @property
    def redis_url(self) -> str:
        return f'redis://{self.REDIS_HOST}:{self.REDIS_PORT}'


class DevelopmentConfig(BaseConfig):
    DEBUG: bool = True

    class Config:
        env_file = '.env_dev'


class TestingConfig(BaseConfig):
    DEBUG = False

    class Config:
        env_file = '.env_test'


class ProductionConfig(BaseConfig):
    DEBUG = False
    SECRET_KEY: str  # 强制要求在生产环境设置 SECRET_KEY
    BACKEND_CORS_ORIGINS: List[str] = []  # 设置为特定的允许域

    class Config:
        env_file = '.env_prod'


@lru_cache()
def get_setting():
    # 根据环境变量选择配置
    config_classes_gather = {
        'dev': DevelopmentConfig,
        'test': TestingConfig,
        'prod': ProductionConfig
    }
    config_class = config_classes_gather.get(env_var := get_env_var())
    if not config_class:
        raise ValueError(f'Invalid FAST_API_ENV value: {env_var}')

    env_file_path = Path(__file__).parent.joinpath('env').joinpath(f'.env_{env_var}')
    return config_class(_env_file=env_file_path, _env_file_encoding='utf-8')


# 获取当前配置实例
setting = get_setting()
