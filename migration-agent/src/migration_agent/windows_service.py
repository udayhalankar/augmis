from __future__ import annotations

"""
Optional Windows service wrapper.

This module is intentionally thin so local development can run without pywin32.
Install the optional dependency set `windows-service` to use it.
"""

import threading
import logging
import os
import sys
import tempfile
from pathlib import Path

from migration_agent.config import load_config
from migration_agent.service import main_service_loop

try:
    import win32service  # type: ignore
    import win32serviceutil  # type: ignore
except ImportError:  # pragma: no cover - optional dependency
    win32service = None  # type: ignore[assignment]
    win32serviceutil = None  # type: ignore[assignment]


def _bootstrap_log(message: str) -> None:
    try:
        program_data = os.getenv("PROGRAMDATA") or tempfile.gettempdir()
        log_path = Path(program_data) / "MigrationAgent" / "bootstrap.log"
        log_path.parent.mkdir(parents=True, exist_ok=True)
        with log_path.open("a", encoding="utf-8") as handle:
            handle.write(message + "\n")
    except Exception:
        pass


_bootstrap_log("migration_agent.windows_service imported")


if win32serviceutil is not None:
    class MigrationAgentService(win32serviceutil.ServiceFramework):  # type: ignore[misc]
        _svc_name_ = "MigrationAgent"
        _svc_display_name_ = "Migration Agent"
        _svc_description_ = "Local-first folder watcher and sync agent"
        _exe_name_ = sys.executable
        _exe_args_ = f'"{Path(__file__).resolve()}"'

        def __init__(self, args):
            super().__init__(args)
            self.stop_event = threading.Event()
            self.worker = None
            program_data = os.getenv("PROGRAMDATA") or tempfile.gettempdir()
            self.log_path = Path(program_data) / "MigrationAgent" / "service.log"
            self.log_path.parent.mkdir(parents=True, exist_ok=True)
            logging.basicConfig(
                filename=str(self.log_path),
                level=logging.INFO,
                format="%(asctime)s %(levelname)s %(name)s %(message)s",
            )
            self.logger = logging.getLogger("migration_agent.service")
            self.logger.info("Service object initialized")

        def SvcStop(self):
            self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
            self.stop_event.set()
            if self.worker and self.worker.is_alive():
                self.worker.join(timeout=10)
            self.logger.info("Service stop requested")

        def SvcDoRun(self):
            config = load_config()
            if not config.root_path:
                raise RuntimeError("MIGRATION_AGENT_ROOT_PATH must be set for the Windows service")
            self.logger.info("Service starting with root_path=%s backend_url=%s", config.root_path, config.backend_url)
            self.ReportServiceStatus(win32service.SERVICE_START_PENDING)
            self.ReportServiceStatus(win32service.SERVICE_RUNNING)
            self.worker = threading.Thread(
                target=main_service_loop,
                args=(config.root_path, self.stop_event),
                daemon=True,
            )
            self.worker.start()
            while not self.stop_event.wait(1):
                pass
            self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
            self.ReportServiceStatus(win32service.SERVICE_STOPPED)
            self.logger.info("Service stopped")


def run_windows_service() -> None:
    if win32serviceutil is None:
        raise RuntimeError(
            "Windows service support requires the optional 'windows-service' dependency."
        )
    win32serviceutil.HandleCommandLine(
        MigrationAgentService,
        serviceClassString="migration_agent.windows_service.MigrationAgentService",
    )


def main() -> None:
    if len(sys.argv) == 1:
        if win32serviceutil is None:
            raise RuntimeError(
                "Windows service support requires the optional 'windows-service' dependency."
            )
        import servicemanager  # type: ignore

        servicemanager.Initialize()
        servicemanager.PrepareToHostSingle(MigrationAgentService)
        servicemanager.StartServiceCtrlDispatcher()
        return

    run_windows_service()


if __name__ == "__main__":
    main()
