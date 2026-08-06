# Migration Agent

Standalone local-first agent scaffold for the Augmis/Infomentica deployment.

## What this does
- Scans a local folder on the customer machine.
- Produces a normalized inventory of files and folders.
- Registers with the backend and syncs scan results through a simple API contract.
- Watches folders using polling so it can detect changes automatically.
- Can be wrapped as a Windows service for long-running local installs.

## Local dev
```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -e .
migration-agent scan --root "D:\Infomentica_POCs\Datasource"
```

To watch for changes:
```powershell
migration-agent watch --root "D:\Infomentica_POCs\Datasource" --interval 5
```

To run the service loop directly:
```powershell
migration-agent service --root "D:\Infomentica_POCs\Datasource"
```

To open the local monitor window:
```powershell
migration-agent-ui
```

If the editable venv has not been reinstalled yet, you can launch the same monitor directly with:
```powershell
.\launch-monitor.ps1
```

## Install as a Windows service
```powershell
pip install -e ".[windows-service]"
# create migration-agent\.env with the values below if you want persistent config
python -m migration_agent.windows_service install
python -m migration_agent.windows_service start
```

To stop or remove it:
```powershell
python -m migration_agent.windows_service stop
python -m migration_agent.windows_service remove
```

## Environment variables
- `MIGRATION_AGENT_BACKEND_URL`
- `MIGRATION_AGENT_TENANT_ID`
- `MIGRATION_AGENT_TOKEN`
- `MIGRATION_AGENT_ROOT_PATH`

Example `.env`:
```env
MIGRATION_AGENT_BACKEND_URL=http://127.0.0.1:8000
MIGRATION_AGENT_TENANT_ID=TENANT-001
MIGRATION_AGENT_TOKEN=
MIGRATION_AGENT_ROOT_PATH=D:\Infomentica_POCs\Datasource
```

## Backend API contract
- `POST /api/agents/register`
- `POST /api/agents/heartbeat`
- `POST /api/agents/sync`
- `POST /api/agents/changes`

Typical payloads:
- Registration: agent identity, tenant ID, root path, and capabilities.
- Heartbeat: agent ID, status, root path, timestamp, and pending change count.
- Sync: agent ID, root path, timestamp, and a list of created/modified/deleted file changes.

## Next steps
- Implement the matching backend endpoints.
- Add real agent ID issuance and authentication.
- Wire a proper Windows service wrapper for production install/uninstall.

## User input screen
- The first version does not need a GUI.
- Configuration can be entered through environment variables or a small `.env` file.
- If you want a user-facing setup screen later, we can add a simple installer or tray app after the API contract is finalized.
