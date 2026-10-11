#!/usr/bin/env python3
"""The page the user reads to know whether the build came out as designed.

    verdict-page.py <project> [--press DIR] [--lang en|fa] --out page.html

Built from what the checks already found — never from a model's opinion:
  · TRACE.md          every design promise, and whether it is built and has its test
  · press.json        every button, pressed in a real browser (press-check.py --out DIR)
  · .git/factory-verified   whether the full suite passed on exactly the code that is there now
  · ARCHITECTURE.md → Budgets   the slowest click and the size of the code, against their numbers

WHY. After nineteen phases of the first factory app, 2,682 green tests and a green trace, the owner's words
were "I still am not sure it works". Everything that proved the build lived in terminals and
reports written for a programmer. The design was decided on a page the owner could look at; the
build should be judged on one too: one row per promise, green or red, and the screens as they are
served.

The page is English by default; `--lang fa` writes it in Persian, right to left, with Persian digits.

The page says what it does NOT prove, in its own words, at the bottom: a check on fixture data is
not a week on the real account.
"""

from __future__ import annotations

import argparse
import base64
import datetime as _dt
import html
import importlib.util
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import _budgets  # noqa: E402

_spec = importlib.util.spec_from_file_location("trace_check", HERE / "trace-check.py")
trace = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(trace)  # type: ignore[union-attr]

FA_DIGITS = str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹")

STRINGS: dict[str, dict[str, str]] = {
    "en": {
        "dir": "ltr", "title": "Did it come out right?", "other": "Other",
        "sub": "built from the trace table and real checks, not a model's opinion",
        "head_ok": "Everything came out as designed", "head_bad": "{n} item(s) do not match the design",
        "press_ok": "worked", "press_slow": "worked, but slow", "press_dead": "pressed, nothing happened",
        "press_disabled": "disabled, cannot be pressed", "press_error": "gave an error",
        "press_missing": "not on the page", "press_needs-input": "a form must be filled first — not proven",
        "press_skipped": "not checked",
        "st_done": "built", "st_planned": "not built yet", "st_out-of-v1": "outside this version",
        "st_deviation": "differs from the design", "built_no_test": "built, no test",
        "built_not_pressed": "built; not pressed in a browser", "built_tested": "built and tested",
        "ms": "ms", "no_suite": "no recorded test run", "suite_unknown": "tests were green on {d}; could not compare with the current code",
        "suite_good": "all tests went green on exactly this code ({d})",
        "suite_stale": "the code changed after the last green test run — this code is untested",
        "c_promises": "Design promises", "c_buttons": "Buttons", "c_tests": "Tests", "c_slowest": "Slowest click",
        "c_size": "Code size", "pressed_yes": "really pressed in a browser and worked", "pressed_no": "not pressed in a browser",
        "green": "green", "lines": "lines", "limit": "limit: {n}", "no_limit": "no limit set",
        "group_count": "{ok} of {n} right", "col_asked": "What the design asked", "col_result": "Result", "col_id": "ID",
        "screens": "The screens, as served", "not_proven": "What this page does not prove",
        "disclaimer": "The buttons were pressed on a local copy with fixture data, not on the live panel. Click time was measured on this machine; the network distance to the server adds to it. Behaviour with real data is shown only by the real run (the phase marked \"real run\" and a trial week).",
    },
    "fa": {
        "dir": "rtl", "title": "درست درآمد؟", "other": "دیگر",
        "sub": "ساخته‌شده از جدول ردیابی و بررسی‌های واقعی، نه نظر یک مدل",
        "head_ok": "همه‌چیز طبق طرح درآمد", "head_bad": "{n} مورد با طرح نمی‌خواند",
        "press_ok": "کار کرد", "press_slow": "کار کرد ولی کند", "press_dead": "زده شد، هیچ اتفاقی نیفتاد",
        "press_disabled": "غیرفعال، نمی‌شود زد", "press_error": "خطا داد",
        "press_missing": "روی صفحه نیست", "press_needs-input": "اول باید فرم پر شود — ثابت نشد",
        "press_skipped": "بررسی نشد",
        "st_done": "ساخته شده", "st_planned": "هنوز ساخته نشده", "st_out-of-v1": "خارج از این نسخه",
        "st_deviation": "با طرح فرق دارد", "built_no_test": "ساخته شده، بدون تست",
        "built_not_pressed": "ساخته شده؛ در مرورگر زده نشد", "built_tested": "ساخته شده و تست دارد",
        "ms": "میلی‌ثانیه", "no_suite": "هیچ اجرای ثبت‌شده‌ای از تست‌ها نیست",
        "suite_unknown": "تست‌ها در {d} سبز بودند؛ مقایسه با کد فعلی ممکن نشد",
        "suite_good": "همهٔ تست‌ها روی دقیقاً همین کد سبز شدند ({d})",
        "suite_stale": "کد بعد از آخرین اجرای سبز تست‌ها عوض شده — این کد تست نشده است",
        "c_promises": "وعده‌های طراحی", "c_buttons": "دکمه‌ها", "c_tests": "تست‌ها", "c_slowest": "کندترین کلیک",
        "c_size": "حجم کد", "pressed_yes": "در مرورگر واقعاً زده شد و کار کرد", "pressed_no": "در مرورگر زده نشد",
        "green": "سبز", "lines": "خط", "limit": "سقف: {n}", "no_limit": "سقفی تعیین نشده",
        "group_count": "{ok} از {n} درست", "col_asked": "آنچه طرح خواسته", "col_result": "نتیجه", "col_id": "شناسه",
        "screens": "صفحه‌ها، همان‌طور که سرو می‌شوند", "not_proven": "این صفحه چه چیزی را ثابت نمی‌کند",
        "disclaimer": "دکمه‌ها روی یک نسخهٔ محلی با دادهٔ آزمایشی زده شده‌اند، نه روی پنل واقعی. زمان کلیک روی همین سیستم اندازه گرفته شده؛ فاصلهٔ اینترنت تا سرور به آن اضافه می‌شود. رفتار با دادهٔ واقعی را فقط اجرای واقعی (فاز «اجرای واقعی» و هفتهٔ آزمایشی) نشان می‌دهد.",
    },
}
PRESS_CLASS = {"ok": "good", "slow": "bad", "dead": "bad", "disabled": "bad", "error": "bad",
               "missing": "bad", "needs-input": "warn", "skipped": "bad"}
LANG = "en"


def t(key: str, **kw: object) -> str:
    text = STRINGS[LANG][key]
    return text.format(**kw) if kw else text


def num(x: object) -> str:
    """A number for the page — Persian digits and separators only on the Persian page."""
    text = f"{x:,}" if isinstance(x, int) else str(x)
    return text.translate(FA_DIGITS).replace(",", "٬") if LANG == "fa" else text


def esc(s: str) -> str:
    return html.escape(s or "")


def suite_state(project: Path) -> tuple[str, str]:
    """(verdict class, sentence) — did the full suite pass on exactly this code?"""
    git = project / ".git"
    stamp = git / "factory-verified"
    if not stamp.is_file():
        return "bad", t("no_suite")
    rec = json.loads(stamp.read_text(encoding="utf-8"))
    when = num(rec.get("at", "")[:10])
    try:
        sys.path.insert(0, str(HERE))
        import _git
        now = _git.working_tree_id(project)
    except Exception:  # noqa: BLE001 — cannot compare: say so, never claim a match
        return "warn", t("suite_unknown", d=when)
    if now == rec.get("tree"):
        return "good", t("suite_good", d=when)
    return "bad", t("suite_stale")


def page(project: Path, press: dict | None, press_dir: Path | None) -> str:
    rows, _ = trace.read_trace(project / "TRACE.md") if (project / "TRACE.md").is_file() else ([], False)
    by_id = {r["id"]: r for r in (press or {}).get("results", [])}
    budgets = _budgets.read(project)
    code, _parts = _budgets.count(project)
    suite_cls, suite_text = suite_state(project)

    live = [r for r in rows if r["status"].lower() != "out-of-v1"]
    built = [r for r in live if r["status"].lower() == "done" and r["verified by"]]
    buttons = [r for r in live if r["id"].startswith("B-")]
    pressed_ok = [r for r in buttons if by_id.get(r["id"], {}).get("result") == "ok"]
    slowest = max((x.get("ms", 0) for x in by_id.values()), default=0)

    def status_label(st: str) -> str:
        return STRINGS[LANG].get(f"st_{st}", st)

    def row_verdict(r: dict) -> tuple[str, str]:
        st = r["status"].lower()
        if st == "deviation":
            return ("good" if "approved" in r["item"].lower() else "bad"), status_label("deviation")
        if st != "done" or not r["verified by"]:
            return "bad", status_label(st) if st != "done" else t("built_no_test")
        if r["id"].startswith("B-"):
            if not press:
                return "warn", t("built_not_pressed")
            res = by_id.get(r["id"], {"result": "skipped"})
            kind = res["result"]
            label = STRINGS[LANG].get(f"press_{kind}", kind)
            if res.get("ms"):
                label += f" · {num(res['ms'])} {t('ms')}"
            return PRESS_CLASS.get(kind, "bad"), label
        return "good", t("built_tested")

    verdicts = [(r, *row_verdict(r)) for r in live]
    red = sum(1 for _, c, _ in verdicts if c == "bad")
    code_cls = "good" if budgets.get("code_lines") and code <= budgets["code_lines"] else "bad"
    click_cls = ("warn" if not press else
                 "good" if budgets.get("click_ms") and slowest <= budgets["click_ms"] else "bad")
    if suite_cls == "bad" or code_cls == "bad" or click_cls == "bad":
        red += 1
    headline = t("head_ok") if red == 0 else t("head_bad", n=num(red))

    cards = [
        (t("c_promises"), f"{num(len(built))} / {num(len(live))}", t("built_tested"),
         "good" if len(built) == len(live) else "bad"),
        (t("c_buttons"), f"{num(len(pressed_ok))} / {num(len(buttons))}" if press else "—",
         t("pressed_yes") if press else t("pressed_no"),
         ("good" if len(pressed_ok) == len(buttons) else "bad") if press else "warn"),
        (t("c_tests"), t("green") if suite_cls == "good" else "—", suite_text, suite_cls),
        (t("c_slowest"), f"{num(slowest)} {t('ms')}" if press else "—",
         t("limit", n=num(budgets["click_ms"])) if budgets.get("click_ms") else t("no_limit"), click_cls),
        (t("c_size"), f"{num(code)} {t('lines')}",
         t("limit", n=num(budgets["code_lines"])) if budgets.get("code_lines") else t("no_limit"), code_cls),
    ]

    groups: dict[str, list] = {}
    for r, cls, text in verdicts:
        groups.setdefault(r["design"].split("§")[0].strip() or t("other"), []).append((r, cls, text))

    lang = LANG
    out = [f"""<!doctype html><html lang="{lang}" dir="{t('dir')}"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{t('title')} — {esc(project.name)}</title>
<style>
:root{{--bg:#f6f5f1;--surface:#fff;--ink:#1d1f1c;--muted:#5d625b;--rule:#e2e0d8;
--good:#1f7a4d;--good-bg:#e5f3ea;--bad:#a33a2b;--bad-bg:#f8e6e2;--warn:#8a5a00;--warn-bg:#fbf0d9}}
@media (prefers-color-scheme:dark){{:root:not([data-theme="light"]){{--bg:#121412;--surface:#1b1e1b;
--ink:#ecebe6;--muted:#a9ada5;--rule:#2d312c;--good:#6fd39b;--good-bg:#173323;--bad:#f09a8b;
--bad-bg:#3a1f1a;--warn:#f0c46a;--warn-bg:#352a12}}}}
:root[data-theme="dark"]{{--bg:#121412;--surface:#1b1e1b;--ink:#ecebe6;--muted:#a9ada5;--rule:#2d312c;
--good:#6fd39b;--good-bg:#173323;--bad:#f09a8b;--bad-bg:#3a1f1a;--warn:#f0c46a;--warn-bg:#352a12}}
*{{box-sizing:border-box}} body{{margin:0;background:var(--bg);color:var(--ink);
font-family:system-ui,-apple-system,'Segoe UI',Roboto,Tahoma,sans-serif;line-height:1.7}}
main{{max-width:1080px;margin:0 auto;padding:24px 16px 64px}}
h1{{font-size:1.6rem;margin:0 0 4px}} h2{{font-size:1.15rem;margin:32px 0 10px}}
.sub{{color:var(--muted);margin:0 0 20px}}
.head{{padding:18px 20px;border-radius:14px;font-weight:800;font-size:1.3rem;margin-bottom:18px}}
.cards{{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:10px}}
.card{{background:var(--surface);border:1px solid var(--rule);border-radius:12px;padding:12px 14px}}
.card b{{display:block;font-size:1.25rem}} .card small{{color:var(--muted)}}
.card.good{{border-inline-start:5px solid var(--good)}} .card.bad{{border-inline-start:5px solid var(--bad)}}
.card.warn{{border-inline-start:5px solid var(--warn)}}
.good.head{{background:var(--good-bg);color:var(--good)}} .bad.head{{background:var(--bad-bg);color:var(--bad)}}
.box{{background:var(--surface);border:1px solid var(--rule);border-radius:12px;overflow-x:auto}}
table{{border-collapse:collapse;width:100%;min-width:560px}}
td,th{{padding:8px 12px;border-bottom:1px solid var(--rule);text-align:start;vertical-align:top}}
th{{color:var(--muted);font-weight:600;font-size:.9rem}} tr:last-child td{{border-bottom:0}}
.pill{{display:inline-block;padding:2px 10px;border-radius:99px;font-size:.85rem;white-space:nowrap}}
.pill.good{{background:var(--good-bg);color:var(--good)}} .pill.bad{{background:var(--bad-bg);color:var(--bad)}}
.pill.warn{{background:var(--warn-bg);color:var(--warn)}}
.id{{color:var(--muted);font-size:.85rem;white-space:nowrap}}
details summary{{cursor:pointer;margin:8px 0}}
.shots{{display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:12px}}
.shots figure{{margin:0;background:var(--surface);border:1px solid var(--rule);border-radius:12px;overflow:hidden}}
.shots img{{width:100%;display:block}} .shots figcaption{{padding:6px 10px;color:var(--muted);font-size:.85rem}}
.note{{color:var(--muted);font-size:.95rem}}
</style></head><body><main>
<h1>{t('title')}</h1>
<p class="sub">{esc(project.name)} · {num(_dt.date.today().isoformat())} · {t('sub')}</p>
<div class="head {'good' if red == 0 else 'bad'}">{headline}</div>
<div class="cards">"""]
    for title, big, small, cls in cards:
        out.append(f'<div class="card {cls}">{title}<b>{big}</b><small>{esc(small)}</small></div>')
    out.append("</div>")

    for name, items in groups.items():
        bad = sum(1 for _, c, _ in items if c == "bad")
        out.append(f"<h2>{esc(name)} — {t('group_count', ok=num(len(items) - bad), n=num(len(items)))}</h2>")
        out.append(f'<div class="box"><table><tr><th>{t("col_asked")}</th><th>{t("col_result")}</th>'
                   f'<th>{t("col_id")}</th></tr>')
        for r, cls, text in sorted(items, key=lambda x: x[1] != "bad"):
            out.append(f'<tr><td>{esc(r["item"])}</td><td><span class="pill {cls}">{esc(text)}</span></td>'
                       f'<td class="id">{esc(r["id"])}</td></tr>')
        out.append("</table></div>")

    shots = (press or {}).get("screens", {})
    if shots and press_dir:
        out.append(f"<h2>{t('screens')}</h2><div class='shots'>")
        for route, rel in shots.items():
            f = press_dir / rel
            if f.is_file():
                data = base64.b64encode(f.read_bytes()).decode()
                out.append(f'<figure><img alt="{esc(route)}" src="data:image/jpeg;base64,{data}">'
                           f'<figcaption dir="ltr">{esc(route)}</figcaption></figure>')
        out.append("</div>")

    out.append(f'<h2>{t("not_proven")}</h2>\n<p class="note">{esc(t("disclaimer"))}</p></main></body></html>')
    return "\n".join(out)


def main(argv: list[str]) -> int:
    global LANG
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("project")
    ap.add_argument("--press", help="the --out folder of press-check.py")
    ap.add_argument("--lang", choices=sorted(STRINGS), default="en", help="language of the page")
    ap.add_argument("--out", required=True)
    a = ap.parse_args(argv[1:])
    LANG = a.lang
    project = Path(a.project).expanduser().resolve()
    press_dir = Path(a.press).resolve() if a.press else None
    press = None
    if press_dir and (press_dir / "press.json").is_file():
        press = json.loads((press_dir / "press.json").read_text(encoding="utf-8"))
    Path(a.out).write_text(page(project, press, press_dir), encoding="utf-8")
    print(f"wrote {a.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
