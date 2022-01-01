"""
使用 .env 系统配置"
配置文件

我这种是一种方式，简单直观

还有一种是服务一个固定路径放一个配置文件如 /etc/conf 下 xxx.ini 或者 xxx.py文件
然后项目默认读取 /etc/conf 目录下的配置文件，能读取则为生产环境，
读取不到则为开发环境，开发环境配置可以直接写在代码里面(或者配置ide环境变量)

服务器上设置 ENV 环境变量

更具环境变量 区分生产开发

"""

import os
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv

from settings.base_settings import Settings


# 读取.env环境
# env_path = Path(__file__).parent.parent / '.env'
# load_dotenv(dotenv_path=env_path, verbose=True, override=True)
# 获取环境变量 local-本地环境 .env_test-测试环境, .env_prod 正式环境

@lru_cache()
def get_setting():
    # 更加环境变量读取配置
    env = os.getenv('ENV', '.env_dev')
    env_file_path = Path(__file__).parent.parent / 'env' / env
    return Settings(_env_file=str(env_file_path), _env_file_encoding='utf-8')


if __name__ == '__main__':
    setting = get_setting()
