from __future__ import annotations

import subprocess
import sys
import tkinter as tk
from pathlib import Path
from tkinter import messagebox, ttk

from migration_agent.config import load_config
from migration_agent.state import get_agent_data_dir, load_state


def _env_path() -> Path:
    return Path(__file__).resolve().parents[2] / ".env"


def _read_service_log_tail(max_lines: int = 20) -> str:
    log_path = get_agent_data_dir() / "service.log"
    if not log_path.exists():
        return "No service log found yet."
    try:
        return "\n".join(log_path.read_text(encoding="utf-8").splitlines()[-max_lines:])
    except OSError as exc:
        return f"Unable to read service log: {exc}"


def _read_bootstrap_log_tail(max_lines: int = 10) -> str:
    log_path = get_agent_data_dir() / "bootstrap.log"
    if not log_path.exists():
        return "No bootstrap log found yet."
    try:
        return "\n".join(log_path.read_text(encoding="utf-8").splitlines()[-max_lines:])
    except OSError as exc:
        return f"Unable to read bootstrap log: {exc}"


def _service_status() -> str:
    result = subprocess.run(
        ["sc", "query", "MigrationAgent"],
        capture_output=True,
        text=True,
        check=False,
    )
    output = f"{result.stdout}\n{result.stderr}".upper()
    if "RUNNING" in output:
        return "RUNNING"
    if "STOPPED" in output:
        return "STOPPED"
    return "UNKNOWN"


def _run_service_command(command: str) -> tuple[bool, str]:
    result = subprocess.run(
        [sys.executable, "-m", "migration_agent.windows_service", command],
        capture_output=True,
        text=True,
        check=False,
    )
    output = "\n".join(part for part in [result.stdout.strip(), result.stderr.strip()] if part).strip()
    return result.returncode == 0, output or f"{command} completed."


def _save_root_path(root_path: str) -> None:
    env_path = _env_path()
    lines: list[str] = []
    found = False
    if env_path.exists():
        lines = env_path.read_text(encoding="utf-8").splitlines()
    updated_lines: list[str] = []
    for line in lines:
        if line.startswith("MIGRATION_AGENT_ROOT_PATH="):
            updated_lines.append(f"MIGRATION_AGENT_ROOT_PATH={root_path}")
            found = True
        else:
            updated_lines.append(line)
    if not found:
        updated_lines.append(f"MIGRATION_AGENT_ROOT_PATH={root_path}")
    env_path.write_text("\n".join(updated_lines) + "\n", encoding="utf-8")


class AgentMonitorApp:
    def __init__(self) -> None:
        self.root = tk.Tk()
        self.root.title("Migration Agent Monitor")
        self.root.geometry("980x720")
        self.root.minsize(860, 620)

        self.config = load_config()
        self.status_var = tk.StringVar(value="Checking...")
        self.agent_id_var = tk.StringVar(value="")
        self.tenant_var = tk.StringVar(value=self.config.tenant_id or "")
        self.backend_var = tk.StringVar(value=self.config.backend_url or "")
        self.root_path_var = tk.StringVar(value=self.config.root_path or "")
        self.last_seen_var = tk.StringVar(value="-")
        self.last_sync_var = tk.StringVar(value="-")
        self.pending_var = tk.StringVar(value="0")
        self.message_var = tk.StringVar(value="Ready")
        self._refresh_after_id: str | None = None

        self._build()
        self.refresh()

    def _build(self) -> None:
        container = ttk.Frame(self.root, padding=16)
        container.pack(fill="both", expand=True)
        container.columnconfigure(0, weight=1)

        header = ttk.Frame(container)
        header.grid(row=0, column=0, sticky="ew")
        header.columnconfigure(0, weight=1)

        ttk.Label(header, text="Migration Agent", font=("Segoe UI", 18, "bold")).grid(row=0, column=0, sticky="w")
        ttk.Label(header, textvariable=self.status_var, font=("Segoe UI", 11, "bold")).grid(row=0, column=1, sticky="e")

        summary = ttk.LabelFrame(container, text="Local Status", padding=12)
        summary.grid(row=1, column=0, sticky="ew", pady=(12, 0))
        for index in range(4):
            summary.columnconfigure(index, weight=1)

        self._summary_field(summary, 0, "Agent ID", self.agent_id_var)
        self._summary_field(summary, 1, "Tenant", self.tenant_var)
        self._summary_field(summary, 2, "Last Heartbeat", self.last_seen_var)
        self._summary_field(summary, 3, "Last Sync", self.last_sync_var)
        self._summary_field(summary, 4, "Pending Changes", self.pending_var)
        self._summary_field(summary, 5, "Backend URL", self.backend_var)

        config_frame = ttk.LabelFrame(container, text="Configuration", padding=12)
        config_frame.grid(row=2, column=0, sticky="ew", pady=(12, 0))
        config_frame.columnconfigure(1, weight=1)

        ttk.Label(config_frame, text="Root Path").grid(row=0, column=0, sticky="w", padx=(0, 12))
        ttk.Entry(config_frame, textvariable=self.root_path_var).grid(row=0, column=1, sticky="ew")
        ttk.Button(config_frame, text="Save Root Path", command=self.save_root_path).grid(row=0, column=2, padx=(12, 0))

        action_bar = ttk.Frame(container)
        action_bar.grid(row=3, column=0, sticky="ew", pady=(12, 0))
        ttk.Button(action_bar, text="Start Service", command=lambda: self.run_command("start")).pack(side="left")
        ttk.Button(action_bar, text="Stop Service", command=lambda: self.run_command("stop")).pack(side="left", padx=8)
        ttk.Button(action_bar, text="Restart Service", command=self.restart_service).pack(side="left")
        ttk.Button(action_bar, text="Refresh", command=self.refresh).pack(side="right")

        body = ttk.Panedwindow(container, orient="vertical")
        body.grid(row=4, column=0, sticky="nsew", pady=(12, 0))
        container.rowconfigure(4, weight=1)

        events_frame = ttk.LabelFrame(body, text="Recent Agent Events", padding=8)
        logs_frame = ttk.LabelFrame(body, text="Log Tail", padding=8)
        body.add(events_frame, weight=1)
        body.add(logs_frame, weight=2)

        self.events_list = tk.Listbox(events_frame, height=10)
        self.events_list.pack(fill="both", expand=True)

        self.log_text = tk.Text(logs_frame, wrap="word", height=18)
        self.log_text.pack(fill="both", expand=True)

        footer = ttk.Label(container, textvariable=self.message_var)
        footer.grid(row=5, column=0, sticky="ew", pady=(12, 0))

    def _summary_field(self, parent: ttk.LabelFrame, row: int, label: str, variable: tk.StringVar) -> None:
        ttk.Label(parent, text=label).grid(row=row // 2, column=(row % 2) * 2, sticky="w", pady=4, padx=(0, 8))
        ttk.Label(parent, textvariable=variable).grid(row=row // 2, column=(row % 2) * 2 + 1, sticky="w", pady=4)

    def save_root_path(self) -> None:
        root_path = self.root_path_var.get().strip()
        if not root_path:
            messagebox.showerror("Missing Root Path", "Root path cannot be empty.")
            return
        _save_root_path(root_path)
        self.message_var.set("Root path saved to .env")

    def run_command(self, command: str) -> None:
        ok, output = _run_service_command(command)
        self.message_var.set(output)
        if not ok:
            messagebox.showwarning("Service Command", output)
        self.refresh()

    def restart_service(self) -> None:
        _run_service_command("stop")
        self.run_command("start")

    def refresh(self) -> None:
        if self._refresh_after_id:
            self.root.after_cancel(self._refresh_after_id)
            self._refresh_after_id = None
        state = load_state()
        self.status_var.set(f"Service: {_service_status()}")
        self.agent_id_var.set(str(state.get("agent_id") or "-"))
        self.last_seen_var.set(str(state.get("last_seen_at") or "-"))
        self.last_sync_var.set(str(state.get("last_sync_at") or "-"))
        self.pending_var.set(str(state.get("pending_change_count") or 0))
        self.backend_var.set(str(state.get("backend_url") or self.config.backend_url or "-"))
        self.tenant_var.set(str(state.get("tenant_id") or self.config.tenant_id or "-"))

        self.events_list.delete(0, tk.END)
        recent_events = state.get("recent_events") or []
        for event in recent_events:
            label = f"{event.get('at', '-')}: {event.get('event', 'event')}"
            if event.get("change_count") is not None:
                label += f" ({event['change_count']} changes)"
            if event.get("pending_change_count") is not None:
                label += f" ({event['pending_change_count']} pending)"
            self.events_list.insert(tk.END, label)
        if not recent_events:
            self.events_list.insert(tk.END, "No recent events yet.")

        log_tail = _read_service_log_tail()
        bootstrap_tail = _read_bootstrap_log_tail()
        self.log_text.delete("1.0", tk.END)
        self.log_text.insert(
            tk.END,
            "Service Log\n"
            "===========\n"
            f"{log_tail}\n\n"
            "Bootstrap Log\n"
            "=============\n"
            f"{bootstrap_tail}\n",
        )
        self._refresh_after_id = self.root.after(5000, self.refresh)

    def run(self) -> None:
        self.root.mainloop()


def main() -> None:
    AgentMonitorApp().run()


if __name__ == "__main__":
    main()
