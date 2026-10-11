#!/usr/bin/env python3
"""Tier 2 of the design system's enforcement: per phase, allowed to be slow.

    verify_design.py                             # static checks only
    verify_design.py --project app/              # + escape-hatch census
    verify_design.py --url http://localhost:8000/-/gallery [--url …]

Tier 1 (`ds-lint.py`) runs on every edit and carries only rules decidable from
one file's text with no judgement, because a blocking hook that misfires teaches
an agent to route around it. Everything computed, cross-file, or arguable lives
here instead — including the two checks that can only be made against a page that
has actually been rendered:

  · horizontal overflow at 375px, which is the failure a laptop never shows;
  · contrast MEASURED in a browser rather than read out of the stylesheet, which
    is the only way to catch a colour that is correct in source and wrong on
    screen because something inherited over it.

Those two need Playwright. Without it they are SKIPPED and said to be skipped —
never silently passed, because a check that quietly does nothing is worse than no
check at all.

Exit 0 when everything that ran passed.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from collections import Counter
from pathlib import Path

FACTORY = Path(__file__).resolve().parent.parent
SCRIPTS = FACTORY / "scripts"

# Re-exec under the factory's own venv if Playwright lives there and not here.
# Without this the browser checks SKIP when run as ./verify_design.py — which is
# how it is run — and a skipped check reads as a passing one at a glance. That is
# the failure this whole file exists to avoid.
_VENV = FACTORY / ".venv" / "bin" / "python"
if "playwright" not in sys.modules:
    try:
        import playwright  # noqa: F401
    except ImportError:
        if _VENV.is_file() and Path(sys.executable).resolve() != _VENV.resolve():
            import os
            os.execv(str(_VENV), [str(_VENV), __file__, *sys.argv[1:]])

HATCH = re.compile(r"ds-allow:\s*(D\d+|physical)\s*(?:—|-)?\s*(.*?)\s*(?:#\}|\*/|$)")
HEX = re.compile(r"#[0-9a-fA-F]{3}(?:[0-9a-fA-F]{3})?\b")


class Report:
    def __init__(self) -> None:
        self.failed = False

    def ok(self, what: str, detail: str = "") -> None:
        print(f"  PASS  {what}{(' — ' + detail) if detail else ''}")

    def bad(self, what: str, detail: str) -> None:
        self.failed = True
        print(f"  FAIL  {what} — {detail}", file=sys.stderr)

    def skip(self, what: str, why: str) -> None:
        print(f"  SKIP  {what} — {why}")

    def note(self, text: str) -> None:
        print(f"        {text}")


def run_static(r: Report) -> None:
    print("\nThe system itself")
    for script, label in ((SCRIPTS / "ds-brand-check.py", "every brand fills the contract"),
                          (SCRIPTS / "ds-core-check.py", "core.css is brand-blind")):
        p = subprocess.run([sys.executable, str(script)], capture_output=True, text=True)
        if p.returncode == 0:
            r.ok(label)
        else:
            r.bad(label, (p.stderr or p.stdout).strip().splitlines()[-1][:200])


def hatch_census(r: Report, project: Path) -> None:
    """The escape hatch is legitimate and counted. A rule with no hatch gets
    worked around invisibly; one with a counted hatch gets worked around visibly.
    This is the number that makes 'visibly' true."""
    print("\nEscape hatches")
    tally: Counter[str] = Counter()
    where: list[str] = []
    for f in project.rglob("*"):
        if f.suffix.lower() not in {".html", ".jinja", ".j2", ".css"} or not f.is_file():
            continue
        for n, line in enumerate(f.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
            m = HATCH.search(line)
            if m:
                tally[m.group(1)] += 1
                if not m.group(2).strip():
                    where.append(f"{f}:{n}")
    if not tally:
        r.ok("none used")
        return
    r.ok(f"{sum(tally.values())} in use", ", ".join(f"{k}×{v}" for k, v in tally.most_common()))
    for rid, count in tally.items():
        if count >= 5:
            r.note(f"{rid} is hatched {count} times. At that rate the rule is not "
                   f"being obeyed with exceptions — it is being routed around. "
                   f"Either the rule is wrong or the components are missing a case.")
    for w in where:
        r.bad("a hatch with no reason given", f"{w} — the reason is the whole point")


def fetch(url: str, cookie: str | None = None) -> str | None:
    from urllib.request import Request, urlopen
    try:
        with urlopen(Request(url, headers={"Cookie": cookie} if cookie else {}), timeout=10) as resp:
            return resp.read().decode("utf-8", "replace")
    except Exception as exc:                      # noqa: BLE001
        print(f"  SKIP  {url} — not reachable ({exc})")
        return None


def check_served_html(r: Report, url: str, html: str) -> None:
    """Checks made against what the server actually sent, not against source.

    A template can be clean and the page still wrong: a partial included from
    elsewhere, a string built in Python, a third-party fragment."""
    print(f"\nServed HTML — {url}")

    hexes = HEX.findall(html)
    if hexes:
        r.bad("a colour literal reached the page", f"{len(hexes)}× e.g. {hexes[0]}")
    else:
        r.ok("no colour literal")

    styles = len(re.findall(r"\sstyle\s*=\s*[\"']", html))
    if styles:
        r.bad("an inline style reached the page", f"{styles} found")
    else:
        r.ok("no inline style")

    tables = len(re.findall(r"<table\b", html))
    scrolls = len(re.findall(r"table-scroll", html))
    if tables and scrolls < tables:
        r.bad("a table with no scroll container",
              f"{tables} table(s), {scrolls} container(s) — the page will scroll "
              f"sideways on a phone")
    elif tables:
        r.ok(f"{tables} table(s), each in its own scroll container")

    # JavaScript is enhancement, never mechanism. Counted from the page's own
    # HTML rather than by reading ds.js and believing it.
    forms = len(re.findall(r"<form\b", html))
    onclick = len(re.findall(r"\bon(?:click|submit|change)\s*=", html))
    hrefs = len(re.findall(r'href\s*=\s*["\'](?!#|javascript:)', html))
    if onclick:
        r.bad("behaviour wired inline", f"{onclick} on*= handler(s) — the page stops "
                                        f"working when the script does not run")
    elif forms or hrefs:
        r.ok("mechanism is HTML", f"{forms} form(s), {hrefs} real link(s), 0 inline handlers")


def check_rendered(r: Report, urls: list[str], cookie: str | None = None) -> None:
    """The two checks that need a real browser."""
    print("\nRendered (Playwright)")
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        r.skip("overflow at 375px + measured contrast",
               "playwright not installed. `uv pip install playwright && playwright "
               "install chromium`. These are NOT passing — they did not run.")
        return

    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        for url in urls:
            page = browser.new_page(viewport={"width": 375, "height": 812})
            if cookie:
                # A panel's screens sit behind a login. Without the session they redirect to the
                # sign-in page, and every measurement is of that page instead (the first factory app, 2026-09-24).
                from urllib.parse import urlparse
                page.context.add_cookies([
                    {"name": k.strip(), "value": v.strip(), "domain": urlparse(url).hostname, "path": "/"}
                    for k, v in (c.split("=", 1) for c in cookie.split(";") if "=" in c)])
            try:
                page.goto(url, wait_until="networkidle", timeout=15000)
            except Exception as exc:              # noqa: BLE001
                r.skip(url, f"did not load ({exc})")
                continue
            over = page.evaluate(
                "() => document.documentElement.scrollWidth - "
                "document.documentElement.clientWidth")
            if over > 0:
                r.bad(f"{url} overflows at 375px", f"{over}px of horizontal scroll")
            else:
                r.ok(f"{url} fits 375px")

            # Contrast measured from what the browser actually painted.
            bad = page.evaluate(r"""() => {
              const lum = c => { const [r,g,b] = c.match(/\d+/g).slice(0,3).map(Number)
                  .map(v => (v/=255) <= 0.03928 ? v/12.92 : ((v+0.055)/1.055)**2.4);
                return 0.2126*r + 0.7152*g + 0.0722*b; };
              const bgOf = el => { for (let n = el; n; n = n.parentElement) {
                const b = getComputedStyle(n).backgroundColor;
                if (b && !b.startsWith('rgba(0, 0, 0, 0)')) return b; }
                return 'rgb(255,255,255)'; };
              const out = [];
              document.querySelectorAll('body *').forEach(el => {
                if (!el.textContent.trim() || el.children.length) return;
                const s = getComputedStyle(el);
                if (s.visibility === 'hidden' || s.display === 'none') return;
                const size = parseFloat(s.fontSize);
                const large = size >= 24 || (size >= 18.66 && +s.fontWeight >= 700);
                const l1 = lum(s.color), l2 = lum(bgOf(el));
                const ratio = (Math.max(l1,l2)+0.05)/(Math.min(l1,l2)+0.05);
                if (ratio < (large ? 3 : 4.5))
                  out.push({t: el.textContent.trim().slice(0,30),
                            r: +ratio.toFixed(2), need: large ? 3 : 4.5});
              });
              return out.slice(0, 10);
            }""")
            if bad:
                r.bad(f"{url} contrast, measured in the browser",
                      "; ".join(f"{b['t']!r} at {b['r']}:1 (needs {b['need']})" for b in bad))
            else:
                r.ok(f"{url} every text/background pair passes, measured")
            page.close()
        browser.close()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--project", type=Path, help="directory to census for escape hatches")
    ap.add_argument("--url", action="append", default=[], help="a served page to check")
    ap.add_argument("--cookie", help="a session cookie, name=value, for pages behind a login")
    a = ap.parse_args()

    r = Report()
    run_static(r)
    if a.project:
        hatch_census(r, a.project)
    for url in a.url:
        html = fetch(url, a.cookie)
        if html:
            check_served_html(r, url, html)
    if a.url:
        check_rendered(r, a.url, a.cookie)

    print("\n" + ("FAILED" if r.failed else "OK"))
    return 1 if r.failed else 0


if __name__ == "__main__":
    sys.exit(main())
