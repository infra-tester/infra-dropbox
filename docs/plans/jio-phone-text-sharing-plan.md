# Jio Phone Text Sharing — Implementation Plan

## Goal

Provide a simple, reliable way to share text from a Jio Phone or another small
KaiOS phone, without changing the full experience used on desktop and regular
smartphones.

The phone page is a dedicated, optional view for quick text sharing. It is not
a replacement for the existing home, messages, files, or administrator pages.

## Decisions

- Target Jio Phone / KaiOS browsers first.
- The phone page is text-only: compose, paste, send, and read recent messages.
- Do not show file upload, file browsing, search, or administrator controls there.
- Keep the full application available on regular smartphones and desktop.
- Do not require a shared PIN anywhere in the application.
- Keep administrator-only deletion protected by the configured administrator
  password.
- Make the small-phone page available at an explicit URL (`/m`); do not rely on
  user-agent detection or automatically redirect smartphones.

## Current project context

- Flask page routes are registered in `app/routes/pages.py`.
- Messages are stored with `insert_message()` and read with
  `fetch_message()` in `app/db.py`.
- The existing `/send` handler accepts regular form submissions, while the
  message API is in `app/routes/messages.py`.
- Templates and static assets live under `web/templates` and
  `web/assets`.
- The full home page currently includes both message sharing and file upload.

## Proposed user experience

The `/m` page should be a single, lightweight screen containing:

1. A small app title.
2. One labeled message text area, limited to 200 characters.
3. A **Paste** button.
4. A **Send** button.
5. A short status message for success or validation errors.
6. A plain list of the 10 most recent messages, newest first.

Use simple, single-column HTML with readable text, visible focus, and controls
sized for the phone's directional pad and select key as well as touch. Avoid
frameworks, animations, external assets, complex navigation, and dependencies
on modern JavaScript.

After a successful send, clear the composer and show the new message at the top
of the list. If the browser does not support JavaScript, ordinary form
submission should still send the message and return a usable page with feedback.

## Paste behavior and KaiOS compatibility

Do not assume that a web page on KaiOS can read the system clipboard. Clipboard
APIs may be unavailable or require a secure context, while this app is normally
served over local-network HTTP.

- First verify clipboard behavior on the actual target Jio Phone / KaiOS
  browser.
- If clipboard reading is supported, the Paste button may use it and must show
  a clear error if permission is denied or reading fails.
- If clipboard reading is not supported, keep the text area usable with the
  phone's native paste command and make the Paste button focus the text area
  with a short instruction to use the browser/phone paste action.
- Sending and reading messages must not depend on clipboard support.

## Implementation outline

1. Add `/m` as a separate page route in `app/routes/pages.py`.
   - GET renders the minimal template with a bounded recent-message list.
   - POST validates and stores the submitted text using the existing database
     helper, then renders or redirects with an explicit result.
   - Do not add a separate JSON API unless device testing shows ordinary form
     submission cannot meet the interaction needs.
2. Add a standalone template such as `web/templates/mobile.html`.
   - Do not extend the full `base.html`, whose navigation and scripts load
     controls that the small-phone page does not need.
   - Include viewport metadata, labels, accessible status feedback, and a
     non-JavaScript form path.
3. Add minimal, page-specific CSS and JavaScript only where required.
   - Keep the Send form functional without JavaScript.
   - Treat clipboard support as optional progressive enhancement.
4. Leave `/`, `/messages`, `/files`, existing APIs, and their full-screen
   features available to normal devices.
5. Update the roadmap to reflect that the shared PIN has been dropped, and
   distinguish this small-phone experience from the full administrator
   management work.

## Message handling rules

- Trim leading and trailing whitespace.
- Reject empty or whitespace-only submissions and show an error.
- Enforce the 200-character maximum on the server as well as in the form.
- Reuse the current `message` table and `insert_message()` helper.
- Render recent content as escaped text; do not interpret submitted content as
  HTML.
- Do not add sender identity, expiry, or user-facing deletion.

## Tests and device checks

Add focused Flask tests for:

- `/m` renders the minimal composer and recent messages.
- A valid submission is trimmed, stored, and visible in the recent list.
- Empty and over-limit submissions are rejected with visible feedback and are
  not stored.
- Recent messages are bounded and ordered newest first.
- Existing full home, messages, and files pages remain accessible and retain
  their current features.

Before calling the feature complete, test on the target Jio Phone / KaiOS
browser:

- Page loads and fits the screen without horizontal scrolling.
- Text entry and both buttons work with the device's available controls.
- Native paste works; verify the optional Paste button behavior separately.
- Sending and the recent-message list work on the local network.

## Acceptance criteria

- A Jio Phone user can open `/m`, enter or paste text, send it, and see it in
  the recent list.
- The page remains useful if clipboard APIs or JavaScript are unavailable.
- The phone page does not expose file or administrator controls.
- Desktop and regular-smartphone users can still use the full application.
- No shared PIN is required; administrator-only deletion remains protected.

## Scope and known trade-offs

This plan does not implement a responsive redesign of the full application,
file sharing on KaiOS, live updates, QR codes, or the administrator dashboard.
The app will be open to anyone who can reach it on the LAN: those users can
read shared messages and files and submit messages. Administrator-only
deletion remains password-protected. This is the consequence of removing the
shared PIN, not a feature of the phone page alone.

The existing high-level roadmap currently lists a shared PIN in Phase 5. That
roadmap must be reconciled with this decision before Phase 5 work begins.
