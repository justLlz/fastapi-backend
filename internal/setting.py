import sys
from functools import lru_cache
from pathlib import Path

from internal.config import BaseConfig, DevelopmentConfig, LocalConfig, ProductionConfig, TestingConfig
from pkg import get_env_var


@lru_cache
def init_setting() -> BaseConfig:
    # 根据环境变量选择配置
    config_classes_gather = {
        "dev": DevelopmentConfig,
        "test": TestingConfig,
        "prod": ProductionConfig,
        "local": LocalConfig,
    }
    cur_env_var = get_env_var()
    print(f"Current environment: {cur_env_var}.")

    config_class = config_classes_gather.get(cur_env_var)
    if not config_class:
        print(f"Invalid FAST_API_ENV value: {cur_env_var}")
        sys.exit(1)

    env_file_path = (Path().cwd() / "configs" / f".env.{cur_env_var}").as_posix()
    print(f"Env file path: {env_file_path}.")
    return config_class(_env_file=env_file_path, _env_file_encoding="utf-8")


setting: BaseConfig = init_setting()
print("Init setting successfully.")
