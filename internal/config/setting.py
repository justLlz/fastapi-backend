from functools import lru_cache
from pathlib import Path

from internal.config import BaseConfig, DevelopmentConfig, LocalConfig, ProductionConfig, TestingConfig
from pkg import BASE_DIR, SYS_ENV, colorprint


@lru_cache
def init_setting() -> BaseConfig:
    colorprint.green("Init setting...")
    colorprint.green(f"Current environment: {SYS_ENV}.")

    # 根据环境变量选择配置
    config_classes_gather = {
        "dev": DevelopmentConfig,
        "test": TestingConfig,
        "prod": ProductionConfig,
        "local": LocalConfig,
    }
    config_class = config_classes_gather.get(SYS_ENV)
    if not config_class:
        raise Exception(f"Invalid FAST_API_ENV value: {SYS_ENV}")

    env_file_path = (BASE_DIR / "configs" / f".env.{SYS_ENV}").as_posix()
    # 检查env_file_path是否存在
    if not Path(env_file_path).exists():
        raise Exception(f"Env file not found: {env_file_path}")

    colorprint.green(f"Env file path: {env_file_path}.")
    s = config_class(_env_file=env_file_path, _env_file_encoding="utf-8")
    colorprint.green("Init setting successfully.")
    colorprint.yellow("==========================")
    for k, v in s.dict().items():
        colorprint.yellow(f"{k}: {v}")
    colorprint.yellow("==========================")
    return s


setting: BaseConfig = init_setting()
