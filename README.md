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
  config.py          paths, upload limits, admin password
  db.py              SQLite connection, schema, queries
  security.py        admin authorization helpers
  routes/            blueprints: pages, messages, files, admin
web/                 Everything the browser loads
  templates/         Jinja pages (partials/ for shared fragments)
  assets/            css/, js/, fonts/ served at /assets
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

## Notes

- The app stores data under the user profile in `~/.lan-dropbox`.
- The Windows shutdown control also stores a token in `%LOCALAPPDATA%\InfraDropbox`.
