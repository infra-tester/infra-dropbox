# InfraDropbox

InfraDropbox is a lightweight Flask app for sharing short messages and uploading files from a simple web dashboard.

## Features

- Post and browse messages
- Search stored messages
- Upload and download shared files
- Admin-only deletion controls
- Local app storage for message and file data

## Run locally

1. Open a terminal in the project folder.
2. Ensure your Python environment has the required packages installed (`flask` and `waitress`).
3. Start the app:

```bash
python run.py
```

The app runs on `http://localhost:5000` by default.

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

In the web interface, open "Administrator actions" on the Messages or Files
page and enter the password once to unlock. The sign-in is held in a browser
session cookie, so it survives page reloads but ends when the browser closes
(or when the server restarts). Use the Lock button to end it earlier. When no
password is configured, the administrator panel is hidden and the server
refuses all admin actions.

## Supported file types

In addition to common images and PDF/Office/text files, uploads support
HEIC/HEIF/AVIF/BMP/TIFF images; MP3/WAV/OGG/M4A/AAC/FLAC audio;
MP4/MOV/MKV/WEBM/AVI/3GP video; legacy Office and OpenDocument files; JSON,
XML, YAML, logs; and ZIP/7Z/RAR/TAR/GZ archives. Files are shared as downloads,
not displayed as inline previews. Limits remain 100 MB per file and 2 GB total.

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

The sender and message are added to the shared message workspace together.
Requests are rejected when the secret is unset, missing, or incorrect. No
environment variables are needed on Android; configure the URL and matching
Bearer secret in SMS to URL Forwarder.

## Notes

- The app stores data under the user profile in `~/.lan-dropbox`.
- The Windows shutdown control also stores a token in `%LOCALAPPDATA%\InfraDropbox`.
