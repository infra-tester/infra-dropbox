# Plan — One-page UI and service scripts

**Status:** Approved for implementation
**Date:** 2026-11-21
**Supersedes:** `docs/plans/lan-dropbox-roadmap.md` (deleted — all phases 1–8 complete and the section 8 decisions are closed below)

## 1. Goals

1. Replace the four-page navigation with a single-page UI and section tabs, so moving between Home / Messages / Files / Admin does not require full page loads.
2. Add a checked-in `scripts/` folder with start/stop/status PowerShell scripts so running the app as a background service no longer depends on an external PowerShell profile command.

## 2. Decisions already made

These close the former roadmap section 8 items and other product-level choices:

| Topic | Decision |
|---|---|
| Admin credential | Keep `ADMIN_PASSWORD` environment variable as-is. No stored hash, no change-password flow. |
| Backups | No application backup feature. The operator may manually copy `~/.lan-dropbox` into a OneDrive-synced folder. |
| UI shape | Single page, section tabs (not a long scrolling page). |
| Service scripts | Start / stop / status PowerShell scripts. Not a Windows service or Task Scheduler installer. |
| Old `idb` command | Kept unchanged until the new scripts are verified (see §4). |
| Roadmap document | Deleted; this plan is the current planning record. |

UI details (tab placement, interaction behavior) are intentionally left open for a closer design pass before or during implementation; the structure below is the agreed skeleton.

## 3. One-page UI with section tabs

> Note: exact tab placement, styling, and interaction details are to be confirmed in a short UI design pass. The following is the structural plan.

### 3.1 Routing — `app/routes/pages.py`

- `/` renders one new template, `web/templates/app.html`, containing all four sections.
- `/messages`, `/files`, `/admin` → `redirect("/#messages")` etc., so old links and bookmarks still land on the right section (the hash is handled client-side).
- `/send` POST unchanged (no-JS fallback).
- `/api/network` and all `/api/*` endpoints unchanged.

### 3.2 Template — `web/templates/app.html`

- One `<section>` per area:
  - **Home** — send-message form, upload form, "Open on another device" panel.
  - **Messages** — search input, count, message list container.
  - **Files** — storage usage, count, file list container.
  - **Admin** — both states in the DOM: sign-in form (or "not configured" notice) and signed-in dashboard (overview, settings, danger zone).
- Nav in `base.html` becomes tab controls (anchors like `href="/#home"`).
- No-JS behavior: all sections render stacked; the plain `/send` form still works.
- Load styles once: `base.css`, `admin.css`, `messages.css`, `files.css`. Drop per-page `{% block page_styles %}`.
- After the merge, delete `dashboard.html`, `messages.html`, `files.html`, `admin.html`.
- `web/templates/partials/` remains available if the UI design pass wants shared fragments.

### 3.3 ID reconciliation (required before merging)

Duplicate IDs currently exist across pages and must be renamed uniquely, with JS references updated:

- `file-status` — dashboard upload form vs. Files list.
- `message-send-status` vs. `message-status`.
- Any others found while merging (audit all `id=` attributes across the four templates).

### 3.4 JavaScript — `web/assets/js/`

- New small nav module (section of `common.js` or a `nav.js`): initial section from `location.hash`, tab click handling, `hashchange` for back/forward, `aria-current` updates.
- `admin-page.js`: replace the two `window.location.reload()` calls (after login and lock) with in-place show/hide of sign-in vs. dashboard blocks plus `IDB.refreshAll()`.
- `messages.js`, `files.js`, `admin.js` keep their existing polling and `IDB.onRefresh` wiring; only ID references change.
- CSP unchanged — no inline scripts; all JS served from `/assets`.

### 3.5 CSS — `web/assets/css/`

- Adjust `base.css` nav styles for a tab appearance (active state via existing `aria-current` styling).
- No broader visual redesign in this plan; reuse existing section/card styles. Final look is part of the UI design pass.

### 3.6 Tests — `tests/`

- Update tests asserting GETs/renders of the old page routes (`test_server.py`, `test_convenience.py`, and any others touching `/messages`, `/files`, `/admin` pages): expect redirect-to-hash or the single template.
- API tests unchanged.
- Full suite must pass: `python -m unittest discover -s tests`.

## 4. `scripts/` folder

**New files** (PowerShell, at repo root under `scripts/`):

| Script | Behavior |
|---|---|
| `scripts/start.ps1` | Launch `python run.py` detached (`Start-Process`); stdout/stderr → logs under `%LOCALAPPDATA%\InfraDropbox\` (same directory as lock and shutdown token); wait briefly and report whether port 5000 is listening; refuse with a clear message if the instance lock shows another instance is already running. Uses `.venv\Scripts\python.exe` when present, else `python`. Picks up user-level `setx` variables (`ADMIN_PASSWORD`, `SMS_WEBHOOK_SECRET`). |
| `scripts/stop.ps1` | Read `%LOCALAPPDATA%\InfraDropbox\shutdown.token`, POST to loopback `/__idb_shutdown` with the token header (mirrors `server.py` shutdown middleware), wait for exit; clear message if not running. Never force-kills. |
| `scripts/status.ps1` | Report running state (port/lock), listening LAN URLs (via `/api/network` when up), log paths, and whether `ADMIN_PASSWORD` is set. |

- All scripts resolve the project root from `$PSScriptRoot` so they work from any working directory.
- **No changes** to `server.py`, the instance lock, or the shutdown mechanism — scripts reuse existing behavior.
- **Existing `idb` command:** keep the external PowerShell profile `idb` working unchanged while the new scripts are built and verified. Only after `scripts/` works: update `docs/lan-service.md` and the README run section to use `scripts\start.ps1` / `stop.ps1` / `status.ps1`, then either retire `idb` or make it a thin wrapper around the new scripts (operator's choice at that point).
- **Docs:** `docs/lan-service.md` and the README are updated in the same change that declares `scripts/` verified — not before.

## 5. Out of scope

- Windows service / Task Scheduler installation.
- Stored password hash or in-app password change.
- Backup automation or restore tooling.
- Visual redesign beyond tab navigation; QR codes, push/SSE.
- Pagination of list endpoints (intentionally unpaginated).

## 6. Verification

1. `python -m unittest discover -s tests` — full suite green.
2. Manual UI pass: `scripts\start.ps1` → open `/` → switch all four tabs; reload; browser back/forward; old URLs (`/messages`, `/files`, `/admin`) land on the correct section; admin sign-in and lock work without a full page reload; search, upload, download, delete still work.
3. No-JS check: message form still posts via `/send`.
4. Scripts pass: `status.ps1` before start, `start.ps1`, `status.ps1` while running, `stop.ps1`, `status.ps1` after stop.
5. README no longer points at the deleted roadmap and still matches reality (run instructions, admin password section).

## 7. Implementation order

1. `scripts/` folder (independent of UI; `idb` stays as-is until verified).
2. UI design pass — confirm tab placement/behavior (short discussion).
3. One-page UI implementation + test updates.
