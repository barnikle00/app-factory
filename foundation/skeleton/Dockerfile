# One image for every process — `web` and `jobs` are the same code with different commands.
# Nothing here is a credential or an address: those are settings read at run time (ADR 0007).
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
WORKDIR /srv/app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY alembic.ini ./
COPY alembic ./alembic
COPY app ./app

# Non-root. Any directory a named volume mounts must be made HERE and owned by this user: Docker
# seeds an empty volume from the image's directory, ownership included, and a directory that does
# not exist comes out owned by root. the first factory app's first real connect died on exactly that.
RUN useradd --create-home --uid 10001 app && mkdir -p /data && chown -R app:app /srv/app /data
USER app
# No healthcheck here: only `web` serves /health, so the compose file sets it on `web` alone.
