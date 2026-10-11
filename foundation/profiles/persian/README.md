# Language profile: Persian

A small overlay on the starter kit for an app whose users read Persian: pages in Persian, laid out
right to left, dates on the Jalali calendar in the Tehran time zone, digits shown in Persian.
Nothing in the core changes — the overlay replaces a few files and keeps their public names.

## What it replaces or adds

| File | What it does |
|---|---|
| `app/core/text.py` | `normalize_digits` also folds Arabic `ي`/`ك` into Persian `ی`/`ک` (ADR 0006); `template_filters` returns `number` (Persian digits, `٬` grouping) and `local` (Jalali date in the display zone, default `Asia/Tehran`) |
| `app/web/templates/*.html` | sign-in, home and switches pages in Persian, `lang="fa" dir="rtl"` |
| `app/web/static/base.css` | the Vazirmatn font stack |
| `tests/test_text.py`, `tests/test_pages.py` | the same rules, asserted in Persian |
| `requirements.add.txt` | `jdatetime`, appended to `requirements.txt` |

## How to apply it

`build-spec` step 0 does this when `PROFILE=persian`:

```bash
rsync -a --exclude README.md --exclude requirements.add.txt --exclude adr \
      "${CLAUDE_PLUGIN_ROOT}/foundation/profiles/persian/" "$P/"
cat "${CLAUDE_PLUGIN_ROOT}/foundation/profiles/persian/requirements.add.txt" >> "$P/requirements.txt"
```

## When the project also uses the generic design system

Install it right to left, on the Jalali calendar:

```python
env = install(env, brand="…", app_name="…", dev=settings.dev,
              lang="fa", direction="rtl", calendar="jalali")
```

Ship the Vazirmatn font file with the app (do not fetch it from a CDN; fill `fonts.css`) and name it
in the brand file's `--font-*` slots. Keep Latin digits in number columns and Persian digits in
prose (ADR 0006's *Consequences*). Right-to-left is why the core uses logical properties only.

## Picks added by this profile

`jdatetime` for the Jalali calendar on the server; JalaliDatePicker in the browser (see the
*Language profiles* section of `foundation/stack.md`).
