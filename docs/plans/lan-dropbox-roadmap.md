# LAN Dropbox — High-Level Product Roadmap

## 1. Purpose

LAN Dropbox is a self-hosted sharing tool that runs on a Windows PC and is accessed through a web browser by other devices on the same local network.

Its purpose is to make it easy for a small number of people on the network to share short messages, links, and files without relying on cloud storage or external messaging services.

This document describes the product direction and major areas of work. It is a roadmap, not a detailed technical design or a set of implementation tasks. Each area should be discussed and planned separately before implementation.

## 2. Product principles

- **Local-first:** The server and shared data live on the host PC.
- **LAN-focused:** Other devices access the service over the local network.
- **PIN-protected shared access:** Everyone must enter the shared access PIN before using the application.
- **Simple user experience:** Regular users do not need individual accounts or registration.
- **Shared workspace:** Content is visible to users who have passed the shared access check.
- **Administrator control:** Deleting shared content and changing service settings are administrator-only actions.
- **Small-scale concurrent use:** The application should support a small number of people using it at the same time.
- **Incremental development:** Keep the project understandable and build on the existing Python and Flask application rather than introducing unnecessary complexity.

## 3. Access model

### Regular users

Anyone who can reach the service on the LAN must first provide the shared PIN. After passing that check, regular users should be able to:

- View shared messages and links.
- Send new messages and links.
- Browse shared files.
- Upload files within the configured rules and limits.
- Download files.
- Copy shared text or links.

There is no plan for individual user accounts, registration, or personal identity. The interface should show shared content and its submission time, not a sender or device identity.

Regular users cannot delete messages or files. Deletion belongs exclusively to the administrator.

### Server administrator

The server administrator has a separate, password-protected administration area. The administrator password will be supplied through server-side configuration, such as a configuration file or environment variable, rather than entered as a public registration flow.

Administrator capabilities are expected to include:

- Removing individual messages or files and clearing shared content.
- Setting the allowed file types.
- Setting the maximum size of an individual upload.
- Setting the overall storage limit.
- Viewing storage usage and relevant server information.
- Managing other agreed service settings.

Administrator actions must be authorized and enforced by the server, not merely hidden in the interface.

The project does not currently require an activity-history or audit-log feature.

## 4. Main product areas

The application is expected to grow around these areas:

1. **Home / sharing page** — Enter the shared PIN when required, send a message or link, and see recent shared content.
2. **Messages** — Browse, search, copy, and otherwise use the shared message history.
3. **Files** — Browse uploaded files and upload or download content within administrator-configured rules.
4. **Administrator access** — Enter the administrator credentials to access protected controls.
5. **Administrator dashboard** — Manage shared content, storage limits, file rules, and relevant server settings.

These are product areas, not a final route structure or UI specification.

## 5. High-level roadmap

The order below is a suggested progression. Individual phases may be adjusted after each stage is reviewed.

**Status (2026-11-04):** Phases 1–3 are complete. Phases 4–8 have not started.

### Phase 1 — Establish a reliable sharing foundation

Evolve the current message-sharing prototype into a more dependable feature. Shared items should have enough structure to support display, sorting, and later management. Input validation and consistent handling of submitted content should be part of this foundation.

**Status: complete.** Messages are stored as `id` / `content` / `created_at` records, submissions are trimmed and empty ones rejected, and the feed is ordered newest-first with a character limit and counter.

### Phase 2 — Keep shared content between restarts

Introduce persistent local storage so messages are not lost when the Flask server stops or restarts. SQLite is the proposed starting point for application data because it fits the scale and local nature of this project.

**Status: complete.** Messages live in SQLite at `~/.lan-dropbox/message.db`, with the schema created on startup, so content survives server restarts.

### Phase 3 — Complete the message-sharing experience

Improve the message archive and its everyday use. This includes useful organization, search or filtering, clear feedback, and administrator-only deletion or clearing. Messages should remain available until manually deleted; automatic expiry is not part of the current requirement.

**Status: complete.** The archive lists all messages newest-first, shows a live count, copies content with success/failure feedback, refreshes itself, and reports load failures instead of failing silently. Search filters messages on the server, treating `%` and `_` as literal text. Deletion and clearing are enforced on the server against the `ADMIN_PASSWORD` environment variable; the controls appear only after a password is verified, and when no password is configured the server refuses those actions rather than leaving them open. This is deliberately the smallest possible administrator check and does not replace the shared PIN gate, sessions, or the administrator dashboard planned for Phases 5 and 6.

### Phase 4 — Add file sharing

Introduce a dedicated file-sharing experience. Users should be able to upload, browse, and download files. File storage should remain on the host PC; the application should manage file information and the relationship between stored files and their displayed entries.

The administrator must be able to configure the allowed file types, maximum individual upload size, and overall storage limit. Uploaded files should remain available until manually deleted. The exact defaults and configuration experience belong in a later feature plan.

**Status: not started.** Selected as the next phase; see the note below.

### Phase 5 — Add shared access and administrator controls

Introduce the shared PIN gate for regular users and a separate administrator authentication mechanism. The shared PIN is required for everyone using the application; administrator credentials grant access to additional management controls. The administrator password is supplied through server-side configuration.

Both access mechanisms must be enforced by the server. Their exact setup, session behavior, and recovery process should be planned separately.

### Phase 6 — Build the administrator management experience

Add the protected dashboard for managing messages, files, storage limits, allowed file types, and relevant server settings. Deletion and clearing operations must remain administrator-only. An activity-history feature is not currently required.

### Phase 7 — Improve LAN safety and operational reliability

Review the application as a service used by a small number of devices on a shared network. Address upload and download safety, input validation, access protection, session handling, request limits, configuration and secret handling, and safe deployment settings. Development-only behavior such as Flask debug mode must not be enabled during normal use.

### Phase 8 — Add convenience improvements

Once the core sharing and administration features are reliable, consider improvements such as a QR code for opening the service on another device, clearer connection information, live updates, and better status or error feedback.

**Next phase in focus: Phase 4 — Add file sharing.** File sharing is the largest unmet part of the product purpose, it builds directly on the existing Flask and SQLite foundation, and its first slice does not depend on the access controls introduced in Phase 5. Administrator-configured file rules and limits are deferred until the administrator areas exist; the initial slice will use fixed defaults agreed in a separate feature plan.

## 6. Data and storage direction

The proposed direction is to keep application data and uploaded file contents local to the host PC.

- **Messages and file records:** Store structured information in a local database, with SQLite as the initial preference.
- **Uploaded files:** Store file contents in a dedicated location on the host PC; keep their descriptive information and references in the database.
- **Application settings:** Keep the shared PIN, administrator credential configuration, and service settings on the host, with appropriate protection for sensitive values.
- **Retention:** Shared messages and files remain until manually deleted by the administrator.
- **Storage management:** The administrator can configure an overall storage limit and an individual upload-size limit.

These are high-level direction choices. The database schema, folder layout, backup procedure, exact configuration mechanism, and behavior when storage limits are reached belong in later feature plans.

## 7. Constraints and non-goals for the initial product

- No cloud storage or external messaging dependency.
- No individual user registration or personal user accounts initially.
- No sender or device identity displayed with shared content; show content and submission time.
- No user-facing deletion; only the administrator can delete shared content.
- No automatic expiry of messages or files.
- No activity-history or audit-log feature in the current scope.
- No assumption that the service is intended to be exposed to the public internet.
- No unnecessary framework or infrastructure expansion.
- Keep the implementation approachable and maintainable with Python and Flask.
- The initial expected usage is a small number of concurrent LAN users, not a large public service.

## 8. Remaining decisions for later feature plans

The main product choices above have been made. A few implementation-level or operational choices remain open and should be decided when the relevant feature is planned:

1. **Shared PIN management:** How will the shared PIN be configured, changed, and communicated to users?
2. **PIN sessions:** How long should a user remain authorized before being asked for the PIN again?
3. **File allowlist:** Which file extensions or categories should be enabled by default?
4. **Upload and storage defaults:** What initial individual upload-size and total storage limits should be used?
5. **Storage-limit behavior:** What should users see when an upload would exceed the configured limit?
6. **Administrator credential handling:** Which configuration method should be preferred, and how should the administrator change or recover the credential?
7. **Backups:** What simple backup and restore approach is appropriate for the local database and uploaded files?

These are not reasons to expand this roadmap into a detailed design. They should be resolved in the focused plans for the relevant features.

## 9. How to use this roadmap

This roadmap is intended to keep the overall product direction consistent. It does not authorize implementing every phase at once.

Before starting a phase, discuss its expected behavior and trade-offs, then create a separate focused plan for that piece of work. Update this roadmap only when a product-level decision or the overall direction changes.
