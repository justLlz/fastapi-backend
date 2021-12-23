"""使用 .env 系统配置"""
from pydantic import BaseSettings
from pathlib import Path


class Settings(BaseSettings):
    app_name: str = "Awesome API"
    admin_email: str
    items_per_user: int = 50

    class Config:
        # 设置需要识别的 .env 文件
        env_file = ".env"
        # 设置字符编码
        env_file_encoding = 'utf-8'


env_file_path = Path(__file__).parent.parent / '.env'
settings = Settings(_env_file=str(env_file_path), _env_file_encoding='utf-8')
