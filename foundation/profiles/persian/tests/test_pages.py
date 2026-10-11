"""The pages and endpoints that need no database."""


def test_liveness_touches_nothing(client):
    assert client.get("/health").json() == {"status": "alive"}


def test_the_sign_in_page_is_persian_right_to_left_and_phone_ready(client):
    html = client.get("/login").text
    assert 'lang="fa"' in html and 'dir="rtl"' in html
    assert 'name="viewport" content="width=device-width' in html
    assert '<form method="post" action="/login">' in html


def test_a_page_behind_the_gate_sends_a_visitor_to_sign_in(client):
    r = client.get("/switches")
    assert r.status_code == 303 and r.headers["location"] == "/login?next=/switches"


def test_readiness_without_a_database_says_so(client):
    r = client.get("/health/ready")
    assert r.status_code == 503 and "database" in r.json()["failed"]


def test_nobody_is_handed_the_route_map():
    from fastapi.testclient import TestClient

    from app.web.app import create_app
    from tests.conftest import make_settings

    with TestClient(create_app(make_settings())) as c:
        assert c.get("/openapi.json").status_code == 404 and c.get("/docs").status_code == 404
