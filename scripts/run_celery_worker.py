from internal.celery_tasks.__init__ import default_celery_client, default_queue
import os
import sys


def main() -> None:
    is_windows = os.name == "nt"

    # 可用环境变量覆盖，括号内为默认值
    queues = default_queue
    loglevel = "debug"
    pool = "solo" if is_windows else "prefork"
    concurrency = "1" if is_windows else "4"

    # Windows 下为避免调试器/多进程的已知问题，默认关掉 gossip/mingle/heartbeat
    minimal_flags = ["--without-gossip", "--without-mingle", "--without-heartbeat"] if is_windows else []

    # 允许通过命令行追加更多 Celery 参数（优先级最高）
    # 用法示例：python tools/run_celery_worker.py --logfile=worker.log
    extra_cli_args = sys.argv[1:]

    argv = [
        "worker",
        "-l", loglevel,
        "-Q", queues,
        "--pool", pool,
        "--concurrency", str(concurrency),
        *minimal_flags,
        *extra_cli_args,
    ]

    # 用 worker_main 更稳（避免 Click 解析 "celery" 命令名的问题）
    default_celery_client.app.worker_main(argv)


if __name__ == "__main__":
    main()
