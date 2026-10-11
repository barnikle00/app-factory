# REFERENCE — generated, do not edit

Regenerate with `scripts/ds-reference.py > foundation/design/REFERENCE.md`.

Hand-editing this file is how a colour came to be documented as passing while it failed. Everything below is read out of the system itself: the macro signatures from `templates/ds.html`, the tokens from `core.css`, the slots from `ds-brand-check.py`, the rules from `ds-lint.py`.

## The seventeen macros

```jinja
{% import "ds.html" as ds %}
```

- `ds.button(label, intent="secondary", type="button", href=none, name=none, value=none, disabled=false, size=none, icon=none, attrs="")`
- `ds.actions(primary=none, secondary=[], align="end")`
  - ONE primary slot, by signature
- `ds.field(name, label, kind="text", value="", hint=none, error=none, required=false, placeholder=none, width=none, attrs="")`
  - text, number, date, password, textarea, checkbox
- `ds.select(name, label, options, value=none, hint=none, width=none, attrs="")`
  - writes its own wrapper
- `ds.toolbar(method="get", action="")`
  - the filter bar
- `ds.table(columns, rows, empty_title=none, empty_hint=none, row_key=none, highlight=none)`
  - columns: [{key, label, num=false, width=none, nowrap=false}] rows: list of mappings, or of objects with those attributes. A cell may be pre-rendered: pass the value already wrapped by amount() or pill() and mark the column safe=true.
- `ds.pagination(page, pages, url)`
- `ds.card(title=none, featured=false, aside=none)`
- `ds.stat(label, value, unit=none)`
- `ds.pill(text, intent="neutral")`
- `ds.alert(text, intent="warn", title=none)`
- `ds.empty(title, hint=none, action=none)`
  - written by default, not discovered in production
- `ds.modal(id, title, size=none)`
  - a real <dialog>; ds.js only opens and closes it
- `ds.tabs(items, active)`
  - links, not buttons: JavaScript is enhancement, never the mechanism. Each tab is a real URL, so the page works with JS off and the browser back button behaves.
- `ds.breadcrumb(items)`
- `ds.amount(value, unit=none, negative=none)`
  - Money is read left-to-right even inside right-to-left prose. The macro isolates the direction so the digits cannot reorder, and formats through ds_money so the thousands separator is decided in one place rather than per template.
- `ds.datestamp(value, with_time=false)`
  - the other numeric island

## The brand contract — every brand fills all of these

- **surfaces** — `--surface-page`, `--surface-raised`, `--surface-card`, `--surface-sunken`, `--surface-inverse`
- **ink** — `--ink`, `--ink-muted`, `--ink-on-inverse`, `--ink-accent`
- **action** — `--action`, `--action-ink`, `--action-hover`
- **intent** — `--warn`, `--warn-tint`, `--danger`, `--danger-tint`, `--ok`, `--ok-tint`
- **decor** — `--rule`, `--accent`, `--accent-tint`
- **chrome** — `--chrome`, `--chrome-ink`, `--glass`, `--glass-edge`
- **type** — `--font-display`, `--font-body`, `--font-latin`, `--display-min`, `--lh-text`
- **depth** — `--shadow-rgb`

## Tokens declared by core.css

### L2 — the scales

| token | value | note |
|---|---|---|
| `--space-1` | `0.25rem` | 4px — inside a pill, icon-to-text |
| `--space-2` | `0.5rem` | 8px — inside a control |
| `--space-3` | `0.75rem` | 12px — table cell padding |
| `--space-4` | `1rem` | 16px — the default gap between anything |
| `--space-5` | `1.5rem` | 24px — inside a card |
| `--space-6` | `2rem` | 32px — between cards |
| `--space-7` | `3rem` | 48px — between page sections |
| `--space-8` | `4rem` | 64px — page top/bottom |
| `--radius-1` | `calc(var(--radius-base) * 0.6)` | pills, small chips |
| `--radius-2` | `var(--radius-base)` | controls, inputs, buttons |
| `--radius-3` | `calc(var(--radius-base) * 1.6)` | cards, modals, panels |
| `--radius-pill` | `999px` |  |
| `--text-xs` | `calc(0.75rem  * var(--font-scale))` |  |
| `--text-sm` | `calc(0.875rem * var(--font-scale))` |  |
| `--text-md` | `calc(1rem     * var(--font-scale))` |  |
| `--text-lg` | `calc(1.125rem * var(--font-scale))` |  |
| `--text-xl` | `calc(clamp(1.25rem, 1.1rem + 0.7vw, 1.5rem)  * var(--font…` |  |
| `--text-2xl` | `calc(clamp(1.5rem,  1.3rem + 1.1vw, 2rem)    * var(--font…` |  |
| `--text-3xl` | `calc(clamp(1.875rem, 1.5rem + 1.8vw, 2.75rem) * var(--fon…` |  |
| `--lh-tight` | `1.25` | headings only — tall marks and descenders need room |
| `--lh-body` | `var(--lh-text)` | the brand's line-height floor — see its --lh-text |
| `--weight-body` | `400` |  |
| `--weight-medium` | `500` |  |
| `--weight-bold` | `700` |  |
| `--w-amount` | `9rem` |  |
| `--w-count` | `4.5rem` |  |
| `--w-date` | `7.5rem` |  |
| `--w-status` | `6.5rem` |  |
| `--w-name` | `12rem` |  |
| `--w-search` | `18rem` |  |
| `--w-field` | `100%` | the default: fill the form column |
| `--tap` | `44px` |  |
| `--dur-fast` | `calc(120ms * var(--motion))` |  |
| `--dur` | `calc(200ms * var(--motion))` |  |
| `--ease` | `cubic-bezier(0.2, 0, 0.1, 1)` |  |
| `--ease-out` | `cubic-bezier(0.16, 1, 0.3, 1)` |  |
| `--focus-ring` | `0 0 0 2px var(--surface-page), 0 0 0 4px var(--action)` |  |
| `--density` | `1` | row and control padding multiplier: 0.8 … 1.2 |
| `--page-max` | `80rem` | content column cap |
| `--radius-base` | `10px` | every radius in the system derives from this |
| `--chrome-h` | `3.5rem` | app-bar height |
| `--font-scale` | `1` | whole type ladder |
| `--motion` | `1` | 0 disables every transition in the system |

## The rules the linter enforces

Each has an escape hatch: `{# ds-allow: D<n> — why #}` on the line above, or the same in a CSS comment. Hatches are counted, not hidden.

- **D1** — a colour literal
- **D2** — an inline style
- **D3** — a physical direction in an RTL application
- **D4** — decor used as text
- **D5** — a hand-written <table>
- **D6** — an interactive element with no data-tap
- **D7** — zoom disabled
- **D8** — a gradient
- **D9** — a typeface named outside the brand layer
