# Infra Dropbox on Windows — Background Service

## Scope

- **Windows only.** No Linux or macOS setup is provided.
- Uses the checked-in PowerShell scripts in `scripts/`. They are the single source of truth.
- Not a Windows service or Task Scheduler installer.

## Quick start

```powershell
.\scripts\start.ps1
.\scripts\status.ps1
.\scripts\stop.ps1
```

Scripts resolve the project root from `$PSScriptRoot`, so absolute paths work from any working directory. Install dependencies first with `pip install -r requirements.txt` (normally into `.venv`).

## Scripts

| Script | What it does |
|---|---|
| `start.ps1` | Launches `python run.py` detached (`.venv\Scripts\python.exe` when present, else `python`). Refuses a second instance if port `5000` is listening or the lock is held. Loads user-level `setx` values. Waits up to 15 s and reports PID and port state. |
| `status.ps1` | Reports port/lock/token state, LAN URLs from `/api/network`, log paths, and whether `ADMIN_PASSWORD` and `SMS_WEBHOOK_SECRET` are set. |
| `stop.ps1` | Reads `shutdown.token`, POSTs to `/__idb_shutdown` over loopback with `X-IDB-Shutdown-Token`, waits up to 30 s for exit. Never force-kills. |

No changes were made to `server.py`, the instance lock, or the shutdown middleware; the scripts reuse them.

## PowerShell shortcut: `idb`

The profile function `Invoke-InfraDropbox` is a thin wrapper around the same scripts. The global `idb` alias still works.

| Command | Calls |
|---|---|
| `idb` / `idb start` | `scripts\start.ps1` |
| `idb status` | `scripts\status.ps1` |
| `idb stop` | `scripts\stop.ps1` |

Profile location: `%USERPROFILE%\Documents\WindowsPowerShell\Microsoft.PowerShell_profile.ps1`. Reload it in an open shell with `. $PROFILE`. No launch or shutdown logic remains in the profile.

## Files and port

State and logs live under `%LOCALAPPDATA%\InfraDropbox`:

| File | Purpose |
|---|---|
| `server.lock` | Instance lock; held while the server runs. |
| `shutdown.token` | Loopback shutdown credential; present while the server runs. |
| `server.log` | stdout. |
| `server-error.log` | stderr. |

The server listens on port `5000` on all interfaces and uses Waitress, not Flask debug mode. `status.ps1` prints the usable LAN URLs.

## Environment variables

| Variable | Effect |
|---|---|
| `ADMIN_PASSWORD` | Enables admin actions. Empty or unset disables them. |
| `SMS_WEBHOOK_SECRET` | Enables authenticated SMS forwarding. |

Persist them with `setx NAME "value"`. `start.ps1` reads the user-level values from `HKCU\Environment`, so a new terminal is not required. `status.ps1` only reports whether each variable is set; it never prints the values.

## Network and safety

- Allow inbound TCP `5000` on the trusted private network profile. The app does not change firewall rules.
- Intended for a trusted LAN only. Do not expose it to the public internet.
- Shutdown is loopback-only and token-authenticated. A stale or wrong token is rejected.

## Verification cycle

```powershell
idb status    # before start
idb start
idb status    # while running
idb stop
idb status    # after stop
```

## Not included

- Linux/macOS scripts, systemd, or launchd.
- Windows service or Task Scheduler installation.
- Application backup automation.
