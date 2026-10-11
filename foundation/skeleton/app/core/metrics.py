"""The few numbers that show the app works, served at /metrics. Never a per-person label."""

from __future__ import annotations

from prometheus_client import REGISTRY, Gauge

PROCESS_UP = Gauge("app_process_up", "1 while the process is running", ["process"])
JOB_LAST_SUCCESS_AGE_SECONDS = Gauge(
    "app_job_last_success_age_seconds", "Seconds since the job last succeeded", ["job"]
)


def registry():
    return REGISTRY
