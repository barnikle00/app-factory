# Deploying

Every line below was learned on a real deploy. Read it before the first one.

1. **Writes are off.** Every outside write has a switch that starts off (ADR 0010). After a deploy,
   `GET /health/ready` lists `switches_on` — nothing should be there you did not turn on yourself.
2. **Migrations on purpose:** `docker compose run --rm web alembic upgrade head`, then start.
3. **The first owner:** `docker compose run --rm web python -m app.auth.owner --name "<name>"` —
   the password is printed once.
4. **Every setting reaches the process that reads it.** For each field in `app/core/config.py`
   that differs on the server, check the compose file passes it to every service that reads it.
5. **Volumes and ownership.** A directory a named volume mounts must exist in the image, owned by
   the app user (see the Dockerfile). An existing volume keeps its old ownership.
6. **The reverse proxy.** `http2 on`, a TLS session cache, and `proxy_set_header Connection ""`
   with an upstream keepalive — without them every click pays a new connection and handshake.
7. **After the deploy:** `/health/ready` is 200, no job is overdue, no breaker is open. A 503 names
   what failed; fix that before anything else.
