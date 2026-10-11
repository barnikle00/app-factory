#!/usr/bin/env python3
"""The mobile round: check a clickable prototype before its design is locked.

    prototype-check.py <prototype.html | URL> [--view NAME ... --show "JS using {view}"]

Run it on the prototype itself, in the design stage, before the user locks the design. A problem
found here costs one prototype revision; the same problem found after the build costs a phase.

WHY. the first factory app's own prototype won the look comparison outright against Tabler and the
factory's design system — and was "not responsive at all" on a phone. Measured 2026-09-15: it had
no viewport tag, so a real phone laid every page out at 980px and shrank it, and its eight media
queries never ran. With the tag, the folder list — the most important screen — was still cut off
(448px rows in a 375px screen, inside a box that hides overflow), and 88 of that page's 90
controls were shorter than the 44px a finger needs.

CHECKS, in a 375px window — the layout the page has on a phone once its viewport tag is right:
  1. the page declares a device-width viewport (without it a real phone lays the page out at desktop
     width and shrinks it, so every check below is how it WILL look once the tag is added)
  2. nothing makes the page scroll sideways
  3. nothing is cut off — wider than the screen inside a box that hides overflow
     (wide content that scrolls inside its own box is fine: that is the design rule)
  4. every button, field and select is at least 44px tall
  5. text contrast, measured in the browser, in light and in dark
  6. Persian text is laid out right-to-left — wherever `dir` is set: on <html>, or on the app's
     own wrapper, which is what the first factory app's prototype does

A single-page prototype that renders its screens with JavaScript is checked screen by screen:
  --view accounts --view account --show "S.view='{view}'; render();"

Exit 0 when every check passes on every screen, 1 otherwise.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

PHONE = dict(viewport={"width": 375, "height": 812})
MIN_TAP = 44

PROBE = """(minTap) => {
  const vw = document.documentElement.clientWidth;
  const label = el => el.tagName.toLowerCase() + (el.className && typeof el.className === 'string'
      ? '.' + el.className.trim().split(/\\s+/)[0] : '');
  const visible = el => { const r = el.getBoundingClientRect(), cs = getComputedStyle(el);
      return r.width > 0 && r.height > 0 && cs.visibility !== 'hidden' && cs.display !== 'none'; };
  const meta = document.querySelector('meta[name="viewport"]');
  const out = {
    viewport: !!(meta && /width\\s*=\\s*device-width/.test(meta.content)),
    layoutWidth: vw,
    sideways: document.documentElement.scrollWidth - vw,
    persian: 0, persianRtl: 0,
    clipped: [], tiny: [], tinyCount: 0, controls: 0,
  };
  const seen = new Set();
  document.querySelectorAll('body *').forEach(el => {
    const r = el.getBoundingClientRect();
    if (r.width <= vw + 1 || r.height === 0) return;
    for (let p = el.parentElement; p && p !== document.body; p = p.parentElement) {
      const ox = getComputedStyle(p).overflowX;
      if (ox === 'auto' || ox === 'scroll') return;
      if (ox === 'hidden' || ox === 'clip') {
        const key = label(p);
        if (!seen.has(key)) { seen.add(key); out.clipped.push(key + ' holds ' + Math.round(r.width) + 'px'); }
        return;
      }
    }
  });
  document.querySelectorAll('button, select, textarea, input:not([type=hidden]):not([type=checkbox]):not([type=radio]), [role=button]')
    .forEach(el => {
      if (!visible(el) || el.disabled) return;
      out.controls++;
      const h = el.getBoundingClientRect().height;
      if (h < minTap) { out.tinyCount++; if (out.tiny.length < 5) out.tiny.push(label(el) + ' ' + Math.round(h) + 'px'); }
    });
  document.querySelectorAll('body *').forEach(el => {
    if (el.children.length || !visible(el) || !/[\u0600-\u06FF]/.test(el.textContent)) return;
    out.persian++;
    if (getComputedStyle(el).direction === 'rtl') out.persianRtl++;
  });
  return out;
}"""

CONTRAST = """() => {
  const rgb = c => (c.match(/[\\d.]+/g) || [0, 0, 0, 1]).map(Number);
  const lum = c => { const [r, g, b] = rgb(c).slice(0, 3).map(v => (v /= 255) <= 0.03928 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4);
      return 0.2126 * r + 0.7152 * g + 0.0722 * b; };
  const opaque = c => { const v = rgb(c); return v.length < 4 || v[3] > 0.5; };
  const ground = () => { for (const el of [document.body, document.documentElement]) {
      const b = getComputedStyle(el).backgroundColor; if (b && opaque(b)) return b; }
    return 'rgb(255,255,255)'; };
  const bgOf = el => { for (let n = el; n; n = n.parentElement) {
      const b = getComputedStyle(n).backgroundColor; if (b && opaque(b)) return b; } return ground(); };
  const bad = [];
  document.querySelectorAll('body *').forEach(el => {
    if (el.children.length || !el.textContent.trim() || el.closest('[disabled], [aria-hidden="true"]')) return;
    const s = getComputedStyle(el), r = el.getBoundingClientRect();
    if (s.visibility === 'hidden' || s.display === 'none' || r.width === 0 || parseFloat(s.opacity) < 0.2) return;
    const size = parseFloat(s.fontSize), large = size >= 24 || (size >= 18.66 && +s.fontWeight >= 700);
    const a = lum(s.color), b = lum(bgOf(el)), ratio = (Math.max(a, b) + 0.05) / (Math.min(a, b) + 0.05);
    if (ratio < (large ? 3 : 4.5)) bad.push(`«${el.textContent.trim().slice(0, 24)}» ${ratio.toFixed(2)}:1`);
  });
  return bad;
}"""


def check(target: str, views: list[str], show: str | None) -> int:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("playwright is not installed — `python3 -m pip install playwright` then "
              "`python3 -m playwright install chromium`. "
              "Nothing was checked, and that is not a pass.")
        return 1
    url = target if "://" in target else Path(target).resolve().as_uri()
    screens = views or [None]
    failed = False

    def verdict(ok: bool, text: str) -> None:
        nonlocal failed
        failed |= not ok
        print(f"  {'PASS' if ok else 'FAIL'}  {text}")

    results: dict[str, dict] = {}
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        for scheme in ("light", "dark"):
            ctx = browser.new_context(color_scheme=scheme, **PHONE)
            page = ctx.new_page()
            page.goto(url, wait_until="load")
            page.wait_for_timeout(400)
            for screen in screens:
                if screen is not None:
                    page.evaluate(f"() => {{ {show.replace('{view}', screen)} }}")
                page.evaluate(f"() => {{ document.documentElement.setAttribute('data-theme', '{scheme}');"
                              f" document.documentElement.setAttribute('data-bs-theme', '{scheme}'); }}")
                page.wait_for_timeout(150)
                r = results.setdefault(screen or "page", {})
                if scheme == "light":
                    r["probe"] = page.evaluate(PROBE, MIN_TAP)
                r[scheme] = page.evaluate(CONTRAST)
            ctx.close()
        browser.close()

    for name, r in results.items():
        p = r["probe"]
        print(f"\n{name} — 375px")
        verdict(p["viewport"], "declares a device-width viewport" if p["viewport"] else
                "no device-width viewport tag — a real phone lays this page out at desktop width and "
                "shrinks it; the checks below show how it will look once the tag is added")
        verdict(p["sideways"] <= 0, "no sideways scroll" if p["sideways"] <= 0 else
                f"the page scrolls sideways by {p['sideways']}px")
        verdict(not p["clipped"], "nothing cut off" if not p["clipped"] else
                "cut off inside a box that hides overflow: " + "; ".join(p["clipped"][:4]))
        verdict(p["tinyCount"] == 0, f"all {p['controls']} controls at least {MIN_TAP}px tall" if p["tinyCount"] == 0 else
                f"{p['tinyCount']} of {p['controls']} controls shorter than {MIN_TAP}px: " + ", ".join(p["tiny"]))
        if p["persian"]:
            share = p["persianRtl"] / p["persian"]
            verdict(share >= 0.9, "Persian text is right-to-left" if share >= 0.9 else
                    f"only {p['persianRtl']} of {p['persian']} Persian text blocks are laid out right-to-left")
        for scheme in ("light", "dark"):
            bad = r[scheme]
            verdict(not bad, f"contrast in {scheme}" if not bad else
                    f"contrast in {scheme}: {len(bad)} text(s) too faint — " + ", ".join(bad[:4]))
    print("\nFAILED" if failed else "\nOK — the mobile round is green")
    return 1 if failed else 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("target", help="the prototype file, or a URL")
    ap.add_argument("--view", action="append", default=[], help="a screen name, repeatable")
    ap.add_argument("--show", help="JavaScript that shows a screen; {view} is replaced by its name")
    a = ap.parse_args()
    if a.view and not a.show:
        ap.error("--view needs --show: the JavaScript that switches the prototype to that screen")
    return check(a.target, a.view, a.show)


if __name__ == "__main__":
    sys.exit(main())
