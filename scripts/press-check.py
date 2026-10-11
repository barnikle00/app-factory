#!/usr/bin/env python3
"""Press every traced button in a real browser, and see whether anything happens.

    press-check.py <project> --base-url http://localhost:PORT [--cookie C]
                   [--param id=1 --param fid=3 …] [--out DIR]

For every `B-` row in TRACE.md that is not out-of-v1: open the page of the screen it cites (that
screen's `route:`), find the button by its label, press it, and wait for the page to settle. The
row passes only when the press did something — the address changed, the page changed, or a request
went out — with no server error, no script error, and inside `## Budgets → Click`.

WHY. On the first factory app every button had a row, a phase and a test, and trace-check was green. Then
The owner used the panel on a real account and "Publish" could never be pressed: the dialog disabled
its own button before the reader could tick the box it was asking for. Every test had asked the
server whether a POST would be accepted; none had asked whether the page could send one. A test
that exists is not a button that works. This presses it.

WHAT IT REPORTS, per button:
  ok          pressed, something happened, fast enough
  slow        pressed and worked, but took longer than the click budget
  dead        pressed, and nothing at all happened
  disabled    on the page, but cannot be pressed in the state the route shows
  error       the press produced a server error (5xx) or a script error
  missing     not on the page its screen row names — for a button in a tab, a dialog or a later
              step, give its own row the route that shows it: `route: /folders/{fid}?tab=cap`
  needs-input the browser refused to send an empty required field — listed, not proven
  skipped     the page could not be reached, or its route needs a --param nobody gave

Everything except ok and needs-input fails the check. SKIPPED IS NOT A PASS.

SAFETY. It presses buttons, so it runs only against a local copy with fixture or test data —
never the live panel. A base URL that is not localhost is refused. A confirm() is accepted.

--out DIR writes press.json and one screenshot per screen, which verdict-page.py turns into the
page the user reads.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import re
import sys
import time
from pathlib import Path
from urllib.parse import urlparse

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import _budgets  # noqa: E402

_spec = importlib.util.spec_from_file_location("trace_check", HERE / "trace-check.py")
trace = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(trace)  # type: ignore[union-attr]

LOCAL = {"localhost", "127.0.0.1", "::1", "0.0.0.0"}
PLACEHOLDER = re.compile(r"\{(\w+)\}")
QUIET_S = 0.5          # nothing in flight and nothing changing for this long = settled
SETTLE_LIMIT_S = 15.0
FAILING = {"slow", "dead", "disabled", "error", "missing", "skipped"}

# Every element a person can press. Links count: a server-rendered panel opens a dialog with a link.
FIND = r"""(parts) => {
  const norm = s => (s || '').replace(/\s+/g, ' ').trim();
  const visible = el => { const r = el.getBoundingClientRect(), cs = getComputedStyle(el);
    return r.width > 0 && r.height > 0 && cs.visibility !== 'hidden' && cs.display !== 'none'; };
  const all = [...document.querySelectorAll(
    'button, a[href], input[type=submit], input[type=button], [role=button], summary')];
  const text = el => norm(el.innerText || el.value || el.getAttribute('aria-label') || '');
  const hits = all.filter(el => visible(el) && parts.every(p => text(el).includes(p)));
  hits.sort((a, b) => text(a).length - text(b).length);
  const el = hits[0];
  if (!el) return null;
  document.querySelectorAll('[data-press-target]').forEach(e => e.removeAttribute('data-press-target'));
  el.setAttribute('data-press-target', '1');
  return { disabled: el.disabled === true || el.getAttribute('aria-disabled') === 'true',
           text: text(el) };
}"""
SNAPSHOT = "() => document.body ? document.body.innerHTML.length + ':' + document.body.innerText : ''"
WATCH = """() => { const t0 = performance.now(); window.__pressLast = 0;
  new MutationObserver(() => { window.__pressLast = performance.now() - t0; })
    .observe(document, {subtree: true, childList: true, attributes: true, characterData: true}); }"""
INVALID = """() => { const el = document.querySelector('[data-press-target]');
  const f = el && (el.form || el.closest('form'));
  return !!(f && f.querySelector(':invalid')); }"""


def routes_by_screen(rows: list[dict]) -> dict[str, list[str]]:
    out: dict[str, list[str]] = {}
    for r in rows:
        if r["id"].startswith("S-"):
            out[r["id"][2:]] = [rt.rstrip(";,.)") for rt in trace.ROUTE.findall(r["built in"])]
    return out


def fill(route: str, params: dict[str, str]) -> tuple[str | None, list[str]]:
    need = [p for p in PLACEHOLDER.findall(route) if p not in params]
    if need:
        return None, need
    return PLACEHOLDER.sub(lambda m: params[m.group(1)], route), []


def press_one(browser, base: str, route: str, parts: list[str], cookie: str | None,
              budget_ms: int | None) -> dict:
    ctx = browser.new_context(viewport={"width": 1280, "height": 800})
    if cookie:
        host = urlparse(base).hostname
        ctx.add_cookies([{"name": k.strip(), "value": v.strip(), "domain": host, "path": "/"}
                         for k, v in (c.split("=", 1) for c in cookie.split(";") if "=" in c)])
    page = ctx.new_page()
    errors: list[str] = []
    requests: list[str] = []
    page.on("pageerror", lambda e: errors.append(f"script error: {e}"))
    page.on("dialog", lambda d: d.accept())
    try:
        resp = page.goto(base.rstrip("/") + route, wait_until="networkidle", timeout=15000)
    except Exception as e:  # noqa: BLE001 — unreachable is reported, never passed
        ctx.close()
        return {"result": "skipped", "detail": f"{route} not reachable ({type(e).__name__})"}
    if resp is None or resp.status >= 400:
        ctx.close()
        return {"result": "skipped", "detail": f"{route} answered {resp.status if resp else 'nothing'}"}
    found = page.evaluate(FIND, parts)
    if not found:
        ctx.close()
        return {"result": "missing", "detail": f"not on {route}"}
    if found["disabled"]:
        ctx.close()
        return {"result": "disabled", "detail": f"on {route} but cannot be pressed"}
    before_url, before = page.url, page.evaluate(SNAPSHOT)
    # A GET that changes nothing on the page is not an effect: a panel that polls for live counts
    # sends those whether or not anybody pressed anything. A write or a navigation is.
    page.on("request", lambda r: (r.method != "GET" or r.is_navigation_request())
            and requests.append(r.url))
    page.on("response", lambda r: r.status >= 500 and errors.append(f"server error {r.status} {r.url}"))
    popups: list = []
    ctx.on("page", lambda p: popups.append(p))
    # The time a press takes is when the page last changed or the last answer arrived — not when the
    # browser decided the network had been quiet for half a second, which would add 500 ms to all.
    # And the wait is our own: Playwright's "networkidle" is a load state, reached once when the page
    # first loaded, so waiting for it after a click returns at once — before a fetch has answered.
    inflight: set = set()
    activity: list[float] = []

    def began(r) -> None:
        inflight.add(r)
        activity.append(time.perf_counter())

    def ended(r) -> None:
        inflight.discard(r)
        activity.append(time.perf_counter())

    page.on("request", began)
    page.on("requestfinished", ended)
    page.on("requestfailed", ended)
    page.on("load", lambda _p: activity.append(time.perf_counter()))
    page.evaluate(WATCH)
    t0 = time.perf_counter()
    mutated = 0.0
    try:
        page.click("[data-press-target]", timeout=5000)
        while time.perf_counter() - t0 < SETTLE_LIMIT_S:
            page.wait_for_timeout(50)
            try:
                mutated = max(mutated, page.evaluate("() => window.__pressLast || 0"))
            except Exception:  # noqa: BLE001 — navigating: the old document is gone
                pass
            last = max([t0 + mutated / 1000, *activity])
            if not inflight and time.perf_counter() - last >= QUIET_S:
                break
        else:
            errors.append(f"never settled within {SETTLE_LIMIT_S:.0f} s")
    except Exception as e:  # noqa: BLE001
        errors.append(f"press failed: {type(e).__name__}")
    try:
        changed = page.url != before_url or page.evaluate(SNAPSHOT) != before
        invalid = page.evaluate(INVALID) if not changed else False
    except Exception:  # noqa: BLE001 — the page went away: that is a change
        changed, invalid = True, False
    ms = int(max([mutated, *((t - t0) * 1000 for t in activity if t >= t0)], default=0))
    ctx.close()
    if errors:
        return {"result": "error", "ms": ms, "detail": "; ".join(errors[:2])}
    if not (changed or requests or popups):
        if invalid:
            return {"result": "needs-input", "ms": ms,
                    "detail": f"on {route}, the browser asked for an empty required field first"}
        return {"result": "dead", "ms": ms, "detail": f"pressed on {route}; nothing happened"}
    if budget_ms and ms > budget_ms:
        return {"result": "slow", "ms": ms, "detail": f"{ms} ms on {route}, budget {budget_ms} ms"}
    return {"result": "ok", "ms": ms, "detail": route}


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("project")
    ap.add_argument("--base-url", required=True)
    ap.add_argument("--cookie")
    ap.add_argument("--param", action="append", default=[], help="name=value for a {name} in a route")
    ap.add_argument("--out", help="write press.json and screen shots here")
    a = ap.parse_args(argv[1:])

    if urlparse(a.base_url).hostname not in LOCAL:
        print(f"REFUSED — {a.base_url} is not a local address. press-check presses buttons, so it "
              "runs only against a local copy with fixture data, never a live panel.", file=sys.stderr)
        return 2
    project = Path(a.project).expanduser().resolve()
    rows, header = trace.read_trace(project / "TRACE.md") if (project / "TRACE.md").is_file() else ([], False)
    if not header:
        print(f"{project.name}: no TRACE.md — no buttons to press")
        return 0
    params = dict(p.split("=", 1) for p in a.param if "=" in p)
    budget_ms = _budgets.read(project).get("click_ms")
    screens = routes_by_screen(rows)
    out_dir = Path(a.out).resolve() if a.out else None
    if out_dir:
        (out_dir / "screens").mkdir(parents=True, exist_ok=True)

    from playwright.sync_api import sync_playwright

    results: list[dict] = []
    shots: dict[str, str] = {}
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        for r in rows:
            if not r["id"].startswith("B-") or r["status"].lower() == "out-of-v1":
                continue
            label = trace._norm(r["id"][2:].replace(trace.DYN, " "))
            parts = [p for p in label.split(" ") if p]
            # A button inside a tab, a dialog or a later step is not on its screen's first view.
            # The row names that state as its own route (`route: /x?tab=cap`) and it is tried first;
            # without one, the first factory app's first run could not find 43 of 79 buttons.
            own = [rt.rstrip(";,.)") for rt in trace.ROUTE.findall(r["built in"])]
            targets = own + [rt for ref in trace.REF.findall(r["design"]) for rt in screens.get(ref, [])]
            res: dict = {"result": "skipped", "detail": "its screen row names no route:"}
            for rt in targets:
                url, need = fill(rt, params)
                if url is None:
                    res = {"result": "skipped", "detail": f"{rt} needs --param {', '.join(need)}"}
                    continue
                res = press_one(browser, a.base_url, url, parts, a.cookie, budget_ms)
                res["route"] = url
                if out_dir and url not in shots and res["result"] != "skipped":
                    shot = out_dir / "screens" / (re.sub(r"\W+", "_", url).strip("_") or "root")
                    shot = shot.with_suffix(".jpg")
                    pg = browser.new_page(viewport={"width": 1280, "height": 800})
                    try:
                        pg.goto(a.base_url.rstrip("/") + url, wait_until="networkidle", timeout=15000)
                        pg.screenshot(path=str(shot), type="jpeg", quality=55)
                        shots[url] = str(shot.relative_to(out_dir))
                    except Exception:  # noqa: BLE001 — a missing picture is not a failed button
                        pass
                    pg.close()
                if res["result"] not in ("missing", "skipped"):
                    break
            results.append({"id": r["id"], "item": r["item"], "design": r["design"], **res})
        browser.close()

    width = max((len(x["id"]) for x in results), default=10)
    print(f"PRESS — {project.name} — {len(results)} buttons"
          + (f" · click budget {budget_ms} ms" if budget_ms else " · no click budget in ARCHITECTURE.md"))
    for x in results:
        print(f"  {x['result']:<11} {x['id']:<{width}}  {x.get('detail', '')}")
    counts: dict[str, int] = {}
    for x in results:
        counts[x["result"]] = counts.get(x["result"], 0) + 1
    print("\n" + " · ".join(f"{k} {v}" for k, v in sorted(counts.items())))
    if out_dir:
        (out_dir / "press.json").write_text(json.dumps(
            {"project": project.name, "base_url": a.base_url, "click_budget_ms": budget_ms,
             "results": results, "screens": shots}, ensure_ascii=False, indent=1), encoding="utf-8")
    failed = [x for x in results if x["result"] in FAILING]
    if any(x["result"] == "skipped" for x in results):
        print("SKIPPED is not a pass.")
    print("FAILED" if failed else "OK — every traced button was pressed and did something")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
