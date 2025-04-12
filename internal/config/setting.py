from functools import lru_cache
from pathlib import Path

from internal.config import BaseConfig, DevelopmentConfig, LocalConfig, ProductionConfig, TestingConfig
from pkg import colorprint, get_sys_env_var, BASE_DIR


@lru_cache
def init_setting() -> BaseConfig:
    colorprint.green("Init setting...")
    cur_env_var = get_sys_env_var()
    colorprint.green(f"Current environment: {cur_env_var}.")

    # 根据环境变量选择配置
    config_classes_gather = {
        "dev": DevelopmentConfig,
        "test": TestingConfig,
        "prod": ProductionConfig,
        "local": LocalConfig,
    }
    config_class = config_classes_gather.get(cur_env_var)
    if not config_class:
        raise Exception(f"Invalid FAST_API_ENV value: {cur_env_var}")

    env_file_path = (BASE_DIR / "configs" / f".env.{cur_env_var}").as_posix()
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
