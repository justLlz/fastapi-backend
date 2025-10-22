from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from internal.aps_tasks.tasks import handle_deploy_svc_monitor
from pkg.logger_helper import logger

scheduler = AsyncIOScheduler(timezone="UTC")


def start_scheduler():
    logger.info("Starting scheduler...")

    try:
        scheduler.add_job(
            handle_deploy_svc_monitor,
            trigger=CronTrigger(minute="*", second=0),
            max_instances=50
        )
        scheduler.start()
    except Exception as e:
        logger.error(f"Scheduler startup error: {e}")
        raise e

    logger.info("Scheduler started successfully")


async def shutdown_scheduler():
    logger.info("Stopping scheduler...")
    try:
        scheduler.shutdown(wait=True)  # 等待任务完成
        logger.info("Scheduler stopped gracefully")
    except Exception as e:
        logger.error(f"Scheduler shutdown error: {e}")
