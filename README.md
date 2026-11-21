# InfraDropbox

InfraDropbox is a lightweight Flask app for sharing short messages and uploading files from a simple web dashboard.

## Features

- Post and browse messages
- Search stored messages
- Upload and download shared files
- Admin dashboard for storage limits, file rules, and bulk cleanup
- "Open on another device" panel with the detected LAN addresses and copy buttons
- Local app storage for message and file data

## Run locally

1. Open a terminal in the project folder.
2. Install the pinned dependencies into your Python environment:

```bash
pip install -r requirements.txt
```

3. Start the app:

```bash
python run.py
```

The server listens on port `5000` on all network interfaces. Open
`http://localhost:5000` on this PC, or `http://<this-pc-ip>:5000` from another
device on the same LAN.

## Project structure

```
app/                 Flask application package
  __init__.py        create_app() factory, error handlers, blueprints
  config.py          paths, upload limits, file types, secrets
  db.py              SQLite connection, schema, queries
  security.py        admin authorization helpers
  routes/            blueprints: pages, messages, files, admin
web/                 Everything the browser loads
  templates/         Jinja pages (partials/ for shared fragments)
  assets/            css/ and js/ served at /assets
server.py            Waitress server + shutdown middleware
run.py               Entry point (python run.py)
tests/               unittest suite (python -m unittest discover -s tests)
docs/                Design notes and roadmaps
```

## Admin password

To enable administrator deletion actions, set an environment variable before starting the app:

```bash
set ADMIN_PASSWORD=your-secret-password
python run.py
```

On Linux/macOS, use `export ADMIN_PASSWORD=your-secret-password` instead.

In the web interface, open the **Admin** page and enter the password to sign
in. The sign-in is held in a browser session cookie, so it survives page
reloads but ends when the browser closes (or when the server restarts); use
the Lock button to end it earlier. While signed in, per-item Delete buttons
appear on the Messages and Files pages, and the dashboard exposes storage
limits, the allowed file-type list, and the bulk "clear all" actions. When no
password is configured, the Admin page explains that access is unavailable
and the server refuses all admin actions.

Repeated failed sign-ins temporarily lock further attempts from that device
(an exponentially growing wait, starting at 30 seconds after 5 failures), so
a forgotten password cannot be guessed quickly.

### Changing or recovering the password

The password lives only in the `ADMIN_PASSWORD` environment variable; the
server never stores it on disk. To rotate or recover it:

1. Stop the server.
2. Set a new value (for a persistent Windows setting, use
   `setx ADMIN_PASSWORD "your-new-password"` and open a new terminal so the
   variable is visible to the next start).
3. Start the server again.

Sessions are signed with a key regenerated on every start, so signing out
everyone (including the administrator) is a side effect of every restart.
Setting the variable to an empty value disables administrator access
entirely rather than leaving it open.

## Supported file types

In addition to common images and PDF/Office/text files, uploads support
HEIC/HEIF/AVIF/BMP/TIFF images; MP3/WAV/OGG/M4A/AAC/FLAC audio;
MP4/MOV/MKV/WEBM/AVI/3GP video; legacy Office and OpenDocument files; JSON,
XML, YAML, logs; and ZIP/7Z/RAR/TAR/GZ archives. Files are shared as downloads,
not displayed as inline previews. The per-file limit (default 100 MB), total
storage limit (default 2 GB), and the allowed extension list are defaults —
the administrator can change all three from the Admin dashboard, and changes
apply immediately.

## SMS webhook

To persist the SMS integration secret for your Windows user account, set
`SMS_WEBHOOK_SECRET`. Do not reuse `ADMIN_PASSWORD`:

```powershell
setx SMS_WEBHOOK_SECRET "your-long-random-secret"
```

Close and reopen the terminal, then restart Infra Dropbox for the new setting
to take effect. `ADMIN_PASSWORD` is optional and only enables administrator
deletion actions:

```powershell
setx ADMIN_PASSWORD "your-admin-password"
```

Configure SMS to URL Forwarder to POST JSON to
`http://<server-lan-ip>:5000/api/integrations/sms` with an
`Authorization: Bearer <your-long-random-secret>` header and this body:

```json
{
  "sender": "+919XXXXXXXXX",
  "message": "Forwarded SMS content"
}
```

The sender is stored separately from the message body and shown as its own
label in the shared message workspace. Requests are rejected when the secret
is unset, missing, or incorrect. No environment variables are needed on Android;
configure the URL and matching Bearer secret in SMS to URL Forwarder.

## Notes

- The app stores data under the user profile in `~/.lan-dropbox`.
- The Windows shutdown control also stores a token in `%LOCALAPPDATA%\InfraDropbox`.
