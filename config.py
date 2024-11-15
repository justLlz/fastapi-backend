from functools import lru_cache
from pathlib import Path
from typing import List, Union
from pydantic import IPvAnyAddress
from pydantic.v1 import BaseSettings

from utils import get_env_var


class BaseConfig(BaseSettings):
    DEBUG: bool = True

    ALGORITHM = 'HS256'
    SECRET_KEY: str

    # JWT 配置
    JWT_ALGORITHM: str = 'HS256'
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 8  # 8 天

    # CORS 配置
    BACKEND_CORS_ORIGINS: List[str]

    # MySQL 配置
    MYSQL_USERNAME: str
    MYSQL_PASSWORD: str
    MYSQL_HOST: Union[IPvAnyAddress, str]
    MYSQL_PORT: str
    MYSQL_DATABASE: str

    # design_gpt MySQL 配置
    DESIGN_GPT_MYSQL_USERNAME: str
    DESIGN_GPT_MYSQL_PASSWORD: str
    DESIGN_GPT_MYSQL_HOST: Union[IPvAnyAddress, str]
    DESIGN_GPT_MYSQL_PORT: str
    DESIGN_GPT_MYSQL_DATABASE: str

    # Redis 配置
    REDIS_HOST: str
    REDIS_PASSWORD: str
    REDIS_DB: int
    REDIS_PORT: int

    class Config:
        case_sensitive = True
        env_file_encoding = 'utf-8'

    @property
    def sqlalchemy_database_uri(self) -> str:
        return f'mysql+aiomysql://{self.MYSQL_USERNAME}:{self.MYSQL_PASSWORD}@{self.MYSQL_HOST}:{self.MYSQL_PORT}/{self.MYSQL_DATABASE}?charset=utf8mb4'

    @property
    def sqlalchemy_echo(self) -> bool:
        return self.DEBUG  # 开发环境启用 SQLAlchemy 日志

    @property
    def design_gpt_sqlalchemy_database_uri(self) -> str:
        return f'mysql+aiomysql://{self.DESIGN_GPT_MYSQL_USERNAME}:{self.DESIGN_GPT_MYSQL_PASSWORD}@{self.DESIGN_GPT_MYSQL_HOST}:{self.DESIGN_GPT_MYSQL_PORT}/{self.DESIGN_GPT_MYSQL_DATABASE}?charset=utf8mb4'

    @property
    def design_gpt_sqlalchemy_echo(self) -> bool:
        return self.DEBUG

    @property
    def redis_url(self) -> str:
        return f'redis://{self.REDIS_HOST}:{self.REDIS_PORT}'


class DevelopmentConfig(BaseConfig):
    DEBUG: bool = True

    class Config:
        env_file = '.env_dev'
        env_file_encoding = 'utf-8'


class TestingConfig(BaseConfig):
    DEBUG = True

    class Config:
        env_file = '.env_test'
        env_file_encoding = 'utf-8'


class ProductionConfig(BaseConfig):
    DEBUG = False

    class Config:
        env_file = '.env_prod'
        env_file_encoding = 'utf-8'


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

    env_file_path = Path(__file__).parent.joinpath('env_files').joinpath(f'.env_{env_var}')
    return config_class(_env_file=env_file_path, _env_file_encoding='utf-8')


# 获取当前配置实例
setting = get_setting()
