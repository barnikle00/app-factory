# The starter kit — what every new factory app starts from

The first factory app spent its first three phases building what every panel needs before its first
screen: settings, the database, sign-in, health, jobs, the test setup. This is that work, done once,
lean, and tested — so a new app's phase 01 is already its own subject.

`build-spec` step 0 copies it into the new project and renames `factory-app` to the project's name.
It is a starting point the project owns from then on, not a library it imports.

## What is in it

| Piece | Where | Decision it carries |
|---|---|---|
| Settings per domain, units in the names | `app/core/config.py` | ADR 0007 |
| Input normalised in, numbers and times formatted out (display zone is a setting) | `app/core/text.py` | ADR 0006, 0003 |
| The guard on every outside write, and the switches | `app/core/outside.py`, `switches.py` | ADR 0010 |
| Async engine with pool and statement time limits | `app/db/session.py` | ADR 0008 |
| The foundation tables, one forward-only migration | `app/db/models.py`, `alembic/` | ADR 0001 |
| Sign-in: argon2, signed sliding cookie, one role gate, the owner command | `app/auth/` | — |
| `/health`, `/health/ready` (jobs, breakers, switches), `/metrics` | `app/web/health.py` | ADR 0009, 0010 |
| The jobs process with each job's last success | `app/jobs/runner.py` | ADR 0009 |
| Sign-in, home, switches pages — real forms, phone-ready, English by default | `app/web/` | ADR 0005 |
| Container, compose, deploy checklist | `Dockerfile`, `docker-compose.yml`, `deploy/` | — |
| Tests: pages and rules without a database, data on a real one | `tests/` | Real runs |

**Not in it, on purpose:** the look (it comes from the app's own prototype), any domain table, any
outside client. `base.css` and `home.html` are placeholders the first screen phase replaces.

## Verification command

    .venv/bin/python -m pytest -q && .venv/bin/ruff check . && .venv/bin/pyrefly check

The factory runs this suite on the kit itself (`tests/test_skeleton.py`), so the kit is
never copied into a project broken. A language profile (`foundation/profiles/`) is overlaid on it
and verified the same way.
