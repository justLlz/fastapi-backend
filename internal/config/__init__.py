from pathlib import Path
from typing import List, Union
from urllib.parse import quote_plus

from pydantic import IPvAnyAddress
from pydantic.v1 import BaseSettings

from pkg import project_root_path
from pkg.logger_helper import Logger


class BaseConfig(BaseSettings):
    DEBUG: bool = True

    SECRET_KEY: str

    # JWT 配置
    JWT_ALGORITHM: str = "HS256"

    # CORS 配置
    BACKEND_CORS_ORIGINS: List[str]

    # MySQL 配置
    MYSQL_USERNAME: str
    MYSQL_PASSWORD: str
    MYSQL_HOST: Union[IPvAnyAddress, str]
    MYSQL_PORT: str
    MYSQL_DATABASE: str

    # Redis 配置
    REDIS_HOST: str
    REDIS_PASSWORD: str
    REDIS_DB: int
    REDIS_PORT: int

    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    class Config:
        case_sensitive = True
        env_file_encoding = "utf-8"

    @property
    def sqlalchemy_database_uri(self) -> str:
        return f"mysql+aiomysql://{quote_plus(self.MYSQL_USERNAME)}:{quote_plus(self.MYSQL_PASSWORD)}@{self.MYSQL_HOST}:{self.MYSQL_PORT}/{self.MYSQL_DATABASE}?charset=utf8mb4"

    @property
    def sqlalchemy_echo(self) -> bool:
        return self.DEBUG  # 开发环境启用 SQLAlchemy 日志

    @property
    def redis_url(self) -> str:
        if self.REDIS_PASSWORD == "":
            return f"redis://{quote_plus(self.REDIS_HOST)}:{self.REDIS_PORT}/{self.REDIS_DB}"
        else:
            return f"redis://:{quote_plus(self.REDIS_PASSWORD)}@{quote_plus(self.REDIS_HOST)}:{self.REDIS_PORT}/{self.REDIS_DB}"


class LocalConfig(BaseConfig):
    DEBUG: bool = True

    class Config:
        env_file = (project_root_path / "configs" / ".env.local").as_posix()
        env_file_encoding = "utf-8"


class DevelopmentConfig(BaseConfig):
    DEBUG: bool = True

    class Config:
        env_file = (project_root_path / "configs" / ".env.dev").as_posix()
        env_file_encoding = "utf-8"


class TestingConfig(BaseConfig):
    DEBUG = False

    class Config:
        env_file = (project_root_path / "configs" / ".env.test").as_posix()
        env_file_encoding = "utf-8"


class ProductionConfig(BaseConfig):
    DEBUG = False

    class Config:
        env_file = (project_root_path / "configs" / ".env.prod").as_posix()
        env_file_encoding = "utf-8"
