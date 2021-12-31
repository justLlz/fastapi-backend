"""使用 .env 系统配置"""
from typing import List, Union

from pydantic import BaseSettings, AnyHttpUrl, IPvAnyAddress
from pathlib import Path


class Settings(BaseSettings):
    # DEBUG: bool = True

    # SECRET_KEY 记得保密生产环境 不要直接写在代码里面
    SECRET_KEY: str = "(-ASp+_)-Ulhw0848hnvVG-iqKyJSD&*&^-H3C9mqEqSl8KN-YRzRE"

    # jwt加密算法
    JWT_ALGORITHM: str = "HS256"
    # jwt token过期时间 60 minutes * 24 hours * 8 days = 8 days
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 8

    # 跨域
    BACKEND_CORS_ORIGINS: List[str] = ['*']

    # mysql 配置
    MYSQL_USERNAME: str = 'root'
    MYSQL_PASSWORD: str = "123456"
    MYSQL_HOST: Union[AnyHttpUrl, IPvAnyAddress] = "127.0.0.1"
    MYSQL_DATABASE: str = 'FastAdmin'

    # mysql地址
    SQLALCHEMY_DATABASE_URL = f"mysql+pymysql://{MYSQL_USERNAME}:{MYSQL_PASSWORD}@" \
                              f"{MYSQL_HOST}/{MYSQL_DATABASE}?charset=utf8mb4"

    # redis配置
    REDIS_HOST: str = "127.0.0.1"
    REDIS_PASSWORD: str = ""
    REDIS_DB: int = 0
    REDIS_PORT: int = 6379
    REDIS_URL: str = f"redis://:{REDIS_PASSWORD}@{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}?encoding=utf-8"

    # 基本角色权限 个人没做过权限设置 但是也看过一些开源项目就这样设计吧
    DEFAULT_ROLE: List[dict] = [
        {"role_id": 100, "role_name": "普通员工", "permission_id": 100},
        {"role_id": 500, "role_name": "主管", "permission_id": 500},
        {"role_id": 999, "role_name": "超级管理员", "permission_id": 999, "re_mark": "最高权限的超级管理员"},
    ]

    class Config:
        # 区分大小写
        case_sensitive = True
        # 设置需要识别的 .env 文件
        env_file = '.env'
        # 设置字符编码
        env_file_encoding = 'utf-8'
