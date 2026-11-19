# Phase 6 — Administrator Management Experience

Focused plan for Phase 6 of `lan-dropbox-roadmap.md`.

## Decisions

- **Dedicated route:** a new `/admin` page, consistent with `/`, `/messages`,
  `/files`.
- **Sign-in gate:** the page itself is session-gated — without a session it
  renders only the sign-in screen; with a session it renders the dashboard.
  All management APIs stay behind `require_admin`.
- **Settings storage:** a `setting` key/value table in SQLite, seeded from the
  existing config defaults on first start and synced back into
  `app.config`, so every reader sees live values. Changing a setting applies
  immediately, no restart.
- **Scope:** storage limits (per-file, total) and the allowed file-type
  allowlist. Credential changes (admin password, SMS secret) are Phase 7.
- **Per-page panels removed:** the "Administrator actions" panels disappear
  from `/messages` and `/files`. Those pages show a direct Delete button per
  item only when the session is signed in (status re-checked on page load and
  window focus). Bulk actions — clear all messages, clear all files — exist
  only on `/admin` to avoid accidental mass deletion.

## Page

- `GET /admin` without session → sign-in view (or an explanatory message when
  `ADMIN_PASSWORD` is not configured).
- Dashboard view sections:
  1. **Overview** — message count, file count, storage used vs limit
     (`GET /api/admin/stats`).
  2. **Settings** — per-file limit (MB input), total storage limit (GB
     input), allowed extensions (comma-separated list) →
     `GET/POST /api/admin/settings`.
  3. **Danger zone** — Clear all messages, Clear all files, Lock.
- Nav gains an always-visible Admin link; the page itself gates content.

## API additions

- `GET /api/admin/settings` → `{max_file_bytes, max_storage_bytes,
  allowed_extensions}` (require_admin).
- `POST /api/admin/settings` — validates: positive ints within sane bounds,
  `max_storage >= max_file`, non-empty extension list matching
  `^\.[a-z0-9]+$`; `400` on violation; persists and updates `app.config`
  including `MAX_CONTENT_LENGTH`.
- `GET /api/admin/stats` → `{messages, files, used_bytes, max_bytes,
  max_file_bytes}` (require_admin).
- `POST /api/files/clear` (require_admin) — removes all file rows and unlinks
  their contents.

## Consistency fixes included

- Upload paths read limits from `app.config` (now settings-backed) instead of
  module constants; `MAX_CONTENT_LENGTH` follows the configured per-file limit.
- The hardcoded "100 MB" / "2 GB" error strings (flagged in Phase 5) become
  dynamic via a `format_size()` helper; the `413` handler and the home-page
  upload rules text use it too.
- `ALLOWED_EXTENSIONS` moves into `default_config()` like the other settings.

## Tests

New coverage: `/admin` gate (sign-in view vs dashboard vs unconfigured),
settings round-trip and validation failures, settings enforced by upload
(limits + allowlist), stats gating, `/api/files/clear`, and assertions that
the per-page admin panel is gone from `/messages` and `/files`.

## Out of scope

Credential management and rate limiting (Phase 7); QR/live updates
(Phase 8).
