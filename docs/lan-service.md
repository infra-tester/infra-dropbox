# Running Infra Dropbox on the LAN

The PowerShell profile command `idb` starts Infra Dropbox in the background. The service listens on port `5000` on the host's network interfaces, so other devices on the same LAN can open one of the `LAN URL` addresses printed by `idb`:

```powershell
idb
idb status
idb stop
```

`idb stop` sends a token-authenticated request over loopback and waits for the server to close. It does not force-terminate the process if graceful shutdown fails. Check the reported log paths under `%LOCALAPPDATA%\InfraDropbox` when startup or shutdown reports a problem.

Install the runtime dependencies in the project virtual environment with `pip install -r requirements.txt`. The normal server uses Waitress and does not enable Flask debug mode.

LAN access also depends on the Windows network profile and firewall permitting inbound TCP port `5000`. Configure firewall rules explicitly for the trusted private network if needed; the application does not modify firewall settings. This service is intended for a trusted LAN and should not be exposed directly to the public internet.
