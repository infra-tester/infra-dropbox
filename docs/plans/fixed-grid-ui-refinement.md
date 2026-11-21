# Plan — Fixed-grid UI refinement

**Status:** Draft for review
**Date:** 2026-11-21
**Context:** The one-page UI is complete (see git history: `a49f62c`). The current layout uses fractional columns (`1fr / 1.35fr / 1fr`), which leaves card sizes dependent on content width and makes the page feel unorganized. This plan replaces it with explicit column widths and a deliberate hierarchy.

## 1. Goals

1. **Visual hierarchy** — primary actions, activity, and administration should read in that order at a glance.
2. **List space** — Messages and Files should get predictable, generous room with stable heights.
3. **Admin placement** — Admin should be unobtrusive when locked and aligned with the rest of the grid when unlocked.
4. **Stable layout** — loading data, status messages, and list changes must not shift cards or resize the page.

## 2. Decisions

| Topic | Decision |
|---|---|
| Grid type | Explicit column widths, not fractional `fr` units. Named grid areas; no auto-placement. |
| Navigation | None. Keep the section IDs as scroll anchors for old URLs. |
| Container width | Keep `--content-width: 1200px` for desktop. |
| Visual language | Reuse the existing palette, cards, buttons, and typography. No colour or branding redesign. |
| Lists | Fixed card height with internally scrolling list bodies. No pagination (still out of scope). |
| Admin | Full-width card at the bottom. Compact sign-in when locked; aligned three-column layout when unlocked. |
| JS behaviour | No functional changes. Same IDs, same polling, same in-place sign-in/lock. |
| No-JS | Preserved: all sections visible, `/send` posts normally. |

## 3. Current problems

- Actions are split between the left (Send, LAN) and right (Upload) columns, so there is no single "what I do" area.
- Fractional columns change with the viewport, and `align-items: start` leaves ragged card bottoms.
- Lists grow with content, so a busy day makes the page arbitrarily long.
- Status lines appear and disappear, nudging neighbouring content.
- The admin card uses a different internal grid from the main content, so its columns do not line up with anything above.

## 4. Proposed desktop layout

Fixed three-column workspace, then a full-width admin card:

```
+----------------------------------------------------------------------------------+
| Infra Dropbox                                                    [connection]      |
+----------------------------------------------------------------------------------+
| ACTIONS (320px)   | ACTIVITY (flexible)        | FILES (360px)                    |
| ----------------- | -------------------------- | -------------------------------- |
| Send a message    | Messages                   | Files                            |
| (primary action)  | search + count + list      | storage + count + list           |
|                   |                            |                                  |
| Upload a file     |                            |                                  |
| (primary action)  |                            |                                  |
|                   |                            |                                  |
| Open on another   |                            |                                  |
| device            |                            |                                  |
+----------------------------------------------------------------------------------+
| ADMIN (full width)                                                               |
| locked:  [password] [Sign in]                                                    |
| unlocked: [overview + danger]  |  [settings spanning the remaining columns]     |
+----------------------------------------------------------------------------------+
```

### 4.1 Structure

Introduce explicit wrappers in `web/templates/app.html`:

- `.workspace` — the three-column grid above.
- `.action-rail` — Send, Upload, LAN cards stacked in column 1.
- `.activity` — Messages and Files side by side in columns 2 and 3.
- `.admin-card` — full-width card below the workspace, with its own `.admin-layout` grid.

Keep all current IDs (`home`, `upload`, `lan`, `messages`, `files`, `admin`) unchanged.

### 4.2 Grid rules

```css
.workspace {
  display: grid;
  grid-template-columns: 320px minmax(0, 1fr) 360px;
  grid-template-areas: "actions activity activity";
  gap: 16px;
  align-items: stretch;
}

.activity {
  display: grid;
  grid-template-columns: minmax(0, 1.25fr) minmax(0, 1fr);
  grid-template-areas: "messages files";
  gap: 16px;
}
```

The action rail is fixed at **320px**, Files at **360px**, and Messages takes the remaining space. At a 1200px container that is 320 / 468 / 360 before gaps — enough for Messages to be the widest column and for Files to fit filename cards comfortably.

### 4.3 Hierarchy

- Move Upload into the left rail next to Send so both primary actions sit together; LAN becomes the tertiary item at the bottom of the rail.
- Give Send and Upload a distinct primary-button treatment (the existing accent colour, filled) so they stand out from secondary/ghost buttons.
- Use the existing `.section-heading` pattern for every card: title left, count/status right.
- Keep the connection badge in the header; no new navigation or tabs.

### 4.4 Stable sizing

- `.action-rail` uses `align-content: start` so short cards do not stretch.
- Messages and Files cards stretch to the same height; `.messages` and `.files` get `max-height: 460px; overflow-y: auto`.
- Reserve space for status text with `min-height` on `.admin-status` and `.file-status`, so messages appearing do not shift layout.
- Keep existing "Loading..." placeholders at the list's final height to avoid a jump when the first fetch resolves.

### 4.5 Admin card

- When locked: `.admin-signed-out` renders as a compact single row — label, password field, Sign in button, status — instead of a tall card with empty space.
- When unlocked: `.admin-layout` reuses the 320px / flexible / 360px column rhythm:

```
grid-template-areas:
  "overview settings settings"
  "danger   settings settings";
```

- Overview and Danger zone stack in the left column; Settings spans the rest. Sign-in/lock stay in place via the existing `admin-page.js` show/hide logic — no reloads.

## 5. Responsive behaviour

| Viewport | Layout |
|---|---|
| ≥ 1200px | Fixed three-column workspace as above. |
| 900–1199px | Two columns: 280px action rail + activity column; Messages above Files. Admin inner grid collapses to two columns. |
| < 900px | One column, top to bottom: Send, Upload, Messages, Files, LAN, Admin. |
| < 600px | Same order, 14px card padding, full-width buttons, existing 44px minimum touch targets. |

Use `grid-template-areas` for each breakpoint so the visual order is explicit and independent of DOM order.

## 6. Implementation steps

1. Restructure `web/templates/app.html` wrappers (`.workspace`, `.action-rail`, `.activity`, `.admin-layout`) without changing IDs or JS hooks.
2. Replace `.app-grid` in `web/assets/css/base.css` with the fixed-width grids above; add list height/scroll and reserved status heights.
3. Add the primary-button modifier in `base.css` and apply it to the Send and Upload buttons.
4. Update the responsive blocks to the four breakpoints above.
5. Update tests in `tests/test_convenience.py` and `tests/test_files.py` for the new wrapper classes; keep the redirect and duplicate-ID assertions.
6. Run `python -m unittest discover -s tests`.

No changes are expected in `app/routes/pages.py`, `server.py`, the scripts, API endpoints, or JavaScript behaviour.

## 7. Verification

1. Full suite green: `python -m unittest discover -s tests`.
2. Rendered-page audit: zero duplicate IDs, all section IDs present, no nav links or `nav.js`.
3. Desktop check at 1200px: column widths are 320 / flexible / 360; card bottoms align; Messages is the widest column.
4. Resize through the breakpoints and confirm the documented stacking order, with no horizontal scroll.
5. Add enough messages and files to force internal list scrolling; confirm the page height stays stable.
6. Trigger upload/send status messages and confirm nothing shifts.
7. Admin sign-in and lock work in place; locked admin is compact, unlocked admin columns align with the workspace.
8. No-JS check: all sections visible, `/send` still posts.

## 8. Out of scope

- New features (QR codes, push/SSE, backups, password change).
- Pagination of list endpoints.
- Tabs or any section-hiding navigation.
- Colour/branding redesign beyond the primary-button modifier.
- Changes to the service scripts or shutdown mechanism.

## 9. To confirm before implementation

- Exact fixed widths: **320px** actions / **360px** files (defaults in this plan).
- List body max-height: **460px**.
- Whether the primary-button accent treatment is desired, or the current neutral buttons should stay.
