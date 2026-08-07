import logging

from app.core.config import settings
from app.core.database import SessionLocal
from app.services.augmis_business_listener_service import run_due_listener_scans
from app.services.server_log_service import background_log_context
from app.services.connector_scheduled_runner_service import run_due_repository_syncs


logger = logging.getLogger(__name__)

try:
    from apscheduler.schedulers.background import BackgroundScheduler
except ModuleNotFoundError:  # pragma: no cover - environment-dependent
    BackgroundScheduler = None  # type: ignore[assignment]


_scheduler = None


def get_connector_scheduler_status():
    return {
        "mode": settings.CONNECTOR_SYNC_SCHEDULER_MODE,
        "apscheduler_available": BackgroundScheduler is not None,
        "enabled": settings.CONNECTOR_SYNC_SCHEDULER_MODE == "embedded",
        "interval_minutes": settings.CONNECTOR_SYNC_SCHEDULER_INTERVAL_MINUTES,
        "timezone": settings.CONNECTOR_SYNC_SCHEDULER_TIMEZONE,
        "running": bool(_scheduler and _scheduler.running),
        "persistent": False,
        "multi_replica_safe": settings.CONNECTOR_SYNC_SCHEDULER_MODE == "external",
    }


def start_connector_scheduler():
    global _scheduler

    if BackgroundScheduler is None:
        logger.warning(
            "Connector sync scheduler not started because APScheduler is not installed"
        )
        return None

    if settings.CONNECTOR_SYNC_SCHEDULER_MODE != "embedded":
        logger.info(
            "Connector sync scheduler not started because mode is %s",
            settings.CONNECTOR_SYNC_SCHEDULER_MODE,
        )
        return None

    if _scheduler and _scheduler.running:
        return _scheduler

    scheduler = BackgroundScheduler(timezone=settings.CONNECTOR_SYNC_SCHEDULER_TIMEZONE)
    scheduler.add_job(
        _run_due_syncs_job,
        trigger="interval",
        minutes=settings.CONNECTOR_SYNC_SCHEDULER_INTERVAL_MINUTES,
        id="connector_due_syncs",
        replace_existing=True,
        coalesce=True,
        max_instances=1,
    )
    scheduler.add_job(
        _run_due_listener_scans_job,
        trigger="interval",
        minutes=settings.CONNECTOR_SYNC_SCHEDULER_INTERVAL_MINUTES,
        id="augmis_business_due_listener_scans",
        replace_existing=True,
        coalesce=True,
        max_instances=1,
    )
    scheduler.start()

    _scheduler = scheduler
    logger.info(
        "Connector sync scheduler started with %s-minute interval",
        settings.CONNECTOR_SYNC_SCHEDULER_INTERVAL_MINUTES,
    )
    return scheduler


def stop_connector_scheduler():
    global _scheduler

    if _scheduler and _scheduler.running:
        _scheduler.shutdown(wait=False)
        logger.info("Connector sync scheduler stopped")

    _scheduler = None


def update_connector_scheduler_settings(
    *,
    mode: str,
    interval_minutes: int,
    timezone_name: str,
):
    settings.CONNECTOR_SYNC_SCHEDULER_MODE = mode
    settings.CONNECTOR_SYNC_SCHEDULER_ENABLED = mode == "embedded"
    settings.CONNECTOR_SYNC_SCHEDULER_INTERVAL_MINUTES = interval_minutes
    settings.CONNECTOR_SYNC_SCHEDULER_TIMEZONE = timezone_name

    stop_connector_scheduler()
    start_connector_scheduler()

    return get_connector_scheduler_status()


def _run_due_syncs_job():
    with background_log_context(
        request_id="SCHEDULER-CONNECTOR-DUE-SYNCS",
        route="scheduler://connector_due_syncs",
        method="JOB",
        component="connector_scheduler",
    ):
        db = SessionLocal()

        try:
            result = run_due_repository_syncs(db=db, tenant_id=None, started_by=None)
            logger.info(
                "Connector due-sync job completed: %s repositories considered due",
                result["due_count"],
                extra={"category": "scheduler_run"},
            )
        except Exception:
            logger.exception(
                "Connector due-sync job crashed",
                extra={"category": "scheduler_crash", "is_critical": True},
            )
        finally:
            db.close()


def _run_due_listener_scans_job():
    with background_log_context(
        request_id="SCHEDULER-AUGMIS-DUE-LISTENER-SCANS",
        route="scheduler://augmis_business_due_listener_scans",
        method="JOB",
        component="augmis_business_listener_scheduler",
    ):
        db = SessionLocal()
        try:
            result = run_due_listener_scans(db)
            logger.info(
                "AUGMIS listener due-scan job completed: %s connectors considered due",
                result["due_count"],
                extra={"category": "scheduler_run"},
            )
        except Exception:
            logger.exception(
                "AUGMIS listener due-scan job crashed",
                extra={"category": "scheduler_crash", "is_critical": True},
            )
        finally:
            db.close()
