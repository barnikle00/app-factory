"""ds_dev — the mockup route, the gallery, and the brand switcher.

    from ds_dev import mount
    if settings.dev:
        mount(app, env, design_dir=Path("app/design"), brands=["slate", "forest"])

WHY THIS EXISTS, AND WHY IT IS NOT A DESIGN TOOL. A mockup in Figma, or a
hand-written HTML mockup, is a second source of truth about a UI that also exists
in code. It diverges by definition — measured here: ten of one project's twelve
mockups were copied byte-identically into a second project, tokens redeclared per
file, 287 inline styles, and both are now wrong about what ships.

So the mockup IS the system. `/-/mockup/<name>` renders real macros, real
core.css and the real brand file against fixture data. The user opens it on their
phone and sees the real typeface, the real text direction, real 375px. An approved mockup
is a screen that is already 80% built — promotion swaps the fixture for the real
query and changes nothing visual.

THE HONEST LIMIT: this can only show what the system already knows how to build.
At screen #1 of a brand-new app it has nothing to show. That is what Act 1 — the
one-time visual exploration, before the component set is fixed — is for. This
module is Act 2 and everything after it.

Every route here is dev-only. mount() refuses to run when dev is false.
"""

from __future__ import annotations

import datetime as _dt
from pathlib import Path
from typing import Any

FIXTURES: dict[str, Any] = {
    "gallery_columns": [
        {"key": "when", "label": "Date", "width": "date"},
        {"key": "who", "label": "Seller", "width": "name"},
        {"key": "state", "label": "Status", "width": "status", "safe": True},
        {"key": "sum", "label": "Amount", "num": True, "width": "amount", "safe": True},
    ],
    "gallery_highlight": lambda r: bool(r.get("flag")),
    "gallery_url": lambda p: f"?page={p}",
}


def _rows(env) -> list[dict]:
    """Fixture rows built through the macros themselves, so the gallery exercises
    the real amount() and pill() rather than pre-baked HTML that can drift."""
    ds = env.get_template("ds.html").module
    raw = [
        (_dt.date(2026, 9, 11), "Ada Lovelace", "ok", 48_250_000, False),
        (_dt.date(2026, 9, 10), "Acme Ltd", "warn", 12_400_000, True),
        (_dt.date(2026, 9, 8), "Grace Hopper", "danger", -3_100_000, False),
    ]
    intents = {"ok": "Approved", "warn": "Pending", "danger": "Returned"}
    return [{"when": ds.datestamp(d), "who": w, "state": ds.pill(intents[s], s),
             "sum": ds.amount(v, "USD"), "flag": f} for d, w, s, v, f in raw]


def mount(app, env, *, design_dir: Path, brands: list[str], dev: bool = True,
          prefix: str = "/-") -> None:
    """Attach the dev routes to a FastAPI/Starlette app."""
    if not dev:
        raise RuntimeError(
            "ds_dev.mount() called with dev=False. These routes render fixture "
            "data and expose every brand; they must never be reachable in "
            "production. Guard the call site, not this function."
        )
    from fastapi import HTTPException
    from fastapi.responses import HTMLResponse, RedirectResponse

    design_dir = Path(design_dir)
    mockups = design_dir / "mockups"
    approvals = design_dir / "approved"

    def _render(name: str, brand: str | None = None, **ctx) -> str:
        base: dict[str, Any] = dict(FIXTURES, gallery_rows=_rows(env), ds_brands=brands, **ctx)
        if brand:
            base["ds_brand"] = brand
        return env.get_template(name).render(**base)

    @app.get(prefix + "/gallery", response_class=HTMLResponse)
    def gallery(brand: str | None = None):
        if brand and brand not in brands:
            raise HTTPException(404, f"unknown brand {brand!r}; have {brands}")
        return _render("_gallery.html", brand=brand)

    @app.get(prefix + "/brands", response_class=HTMLResponse)
    def brand_index():
        """Every brand, side by side. The contract is only proved when a second
        brand renders the same gallery correctly without a single core.css edit —
        so this page is the proof, not the documentation of it."""
        frames = "".join(
            f'<figure style="margin:0"><figcaption style="font:14px system-ui;'
            f'padding:8px">{b}</figcaption>'
            f'<iframe src="{prefix}/gallery?brand={b}" style="inline-size:100%;'
            f'block-size:80vh;border:1px solid #ccc" loading="lazy"></iframe>'
            f"</figure>" for b in brands
        )
        # ds-allow: D1 — this page is a dev harness around the system, not a
        # screen the system renders. It deliberately uses no contract slot, so it
        # cannot lie about a brand by borrowing that brand's colours.
        return HTMLResponse(
            f'<!doctype html><html dir="ltr" lang="en"><meta charset="utf-8">'
            f"<title>Brands</title><body style='margin:0;display:grid;"
            f"grid-template-columns:repeat({len(brands)},1fr);gap:8px'>{frames}"
        )

    @app.get(prefix + "/mockup/{name}", response_class=HTMLResponse)
    def mockup(name: str, brand: str | None = None):
        safe = Path(name).name          # no traversal out of mockups/
        path = mockups / f"{safe}.html"
        if not path.is_file():
            have = sorted(p.stem for p in mockups.glob("*.html")) if mockups.is_dir() else []
            raise HTTPException(404, f"no mockup {safe!r}. Have: {have or 'none yet'}")
        approved = (approvals / f"{safe}.md")
        return _render(f"mockups/{safe}.html", brand=brand,
                       ds_mockup=safe,
                       ds_approved=approved.read_text(encoding="utf-8").splitlines()[0]
                       if approved.is_file() else None)

    @app.post(prefix + "/mockup/{name}/approve")
    def approve(name: str):
        """Approval is a dated file in the repo, not a message in a chat. The
        template linter later checks that the promoted screen's macro calls are a
        superset of what was approved — which only works if the approval is an
        artifact someone can diff."""
        safe = Path(name).name
        approvals.mkdir(parents=True, exist_ok=True)
        stamp = _dt.datetime.now().strftime("%Y-%m-%d %H:%M")
        (approvals / f"{safe}.md").write_text(
            f"approved {stamp}\n\nSource of record for the {safe} screen. The "
            f"promoted template's macro calls must remain a superset of the ones "
            f"in mockups/{safe}.html as of this date.\n", encoding="utf-8")
        return RedirectResponse(f"{prefix}/mockup/{safe}", status_code=303)
