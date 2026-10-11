"""Every founding ADR's enforcement block, tested both ways.

A forbid pattern has to do two things, and testing only the first is how a rule
ends up either useless or hated:

  · FIRES on a real violation — otherwise the ADR is decoration, which is the
    measured status quo of this workspace: rules written down, nothing checking.
  · STAYS SILENT on correct code — otherwise it is a hook that cries wolf, and an
    agent that has learned to route around one hook routes around all of them.

So each case below is a real line of Python or HTML, not a string crafted to
match. Run:  python3 -m pytest tests/ -q
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

FACTORY = Path(__file__).resolve().parent.parent
ADRS = FACTORY / "foundation" / "adr"
CHECK = FACTORY / "scripts" / "adr-check.py"

# (adr, relative path inside the project, source line, should_be_blocked)
CASES: list[tuple[str, str, str, bool]] = [
    # 0001 — expand/contract
    # a drop alone is the legitimate contract step; add-and-drop in one file is refused at commit
    ("0001", "alembic/versions/abc_x.py", "    op.drop_column('sale', 'old_total')", False),
    ("0001", "alembic/versions/abc_x.py",
     "    op.alter_column('sale', 'note', new_column_name='comment')", True),
    ("0001", "alembic/versions/abc_x.py",
     "    op.add_column('sale', sa.Column('seller_id', sa.BigInteger(), nullable=False))", True),
    ("0001", "alembic/versions/abc_x.py",
     "    op.add_column('sale', sa.Column('seller_id', sa.BigInteger(), nullable=True))", False),
    ("0001", "alembic/versions/abc_x.py",
     "    op.add_column('sale', sa.Column('n', sa.Integer(), nullable=False, "
     "server_default='0'))", False),
    # a drop in application code is not a migration and must not be touched
    ("0001", "app/services/sale.py", "    frame.drop_column('x')  # pandas", False),

    # 0002 — integer rial
    ("0002", "alembic/versions/abc_x.py",
     "    sa.Column('amount', sa.Numeric(12, 2), nullable=False)", True),
    ("0002", "app/services/sale.py", "    total = float(row.amount) / 10", True),
    ("0002", "app/services/sale.py", "    total = int(row.amount) // 10", False),
    # a genuine rate is not money, and lives in application code
    ("0002", "app/services/rate.py", "    coefficient = float(settings.tax_rate)", False),

    # 0003 — UTC
    ("0003", "app/services/sale.py", "    created = datetime.utcnow()", True),
    ("0003", "app/services/sale.py", "    created = datetime.now()", True),
    ("0003", "app/services/sale.py", "    created = datetime.now(timezone.utc)", False),
    ("0003", "app/web/report.py",
     "    shown = created.astimezone(ZoneInfo('Asia/Tehran'))", False),

    # 0005 — JavaScript is enhancement
    ("0005", "app/templates/sales.html",
     '  <button onclick="save()">ذخیره</button>', True),
    ("0005", "app/templates/sales.html", '  <a href="javascript:void(0)">بیشتر</a>', True),
    ("0005", "app/static/ds.js", "  el.innerHTML = rows.join('');", True),
    ("0005", "app/templates/sales.html",
     '  <button class="btn" type="submit" data-tap>ذخیره</button>', False),
    ("0005", "app/static/ds.js", "  el.textContent = name;", False),

    # 0006 — normalise at the boundary
    ("0006", "app/web/routes.py", "    n = int(request.form['amount'])", True),
    ("0006", "app/web/routes.py",
     "    n = int(normalize_digits(request.form['amount']))", False),
    ("0006", "app/services/sale.py", "    n = int(row.amount)", False),

    # 0007 — every tunable lives in settings; the settings module itself is the exception
    ("0007", "app/services/sync.py", "    token = os.environ['BOT_TOKEN']", True),
    ("0007", "app/core/config.py", "    token = os.environ['BOT_TOKEN']", False),
    ("0007", "app/services/sync.py", '    base = "https://api.manshoor.ir/v1/users"', True),
    ("0007", "app/services/sync.py", "    base = settings.manshoor_api_base_url", False),
    ("0007", "app/core/config.py", '    manshoor_api_base_url: str = "https://api.manshoor.ir"', False),
    ("0007", "app/services/sync.py", "    # docs: https://core.telegram.org/api/folders", False),

    # documentation is not code: the rule must not fire on the file that explains it
    ("0003", "app/services/sale.py", '"""Why we never call datetime.now() here."""', False),
    ("0003", "app/services/sale.py", "# datetime.now() would be naive, so we do not", False),
    ("0017", "app/core/logging.py", "# enforced by the forbid pattern on log.info(text=...)", False),

    # 0008 — every outside call has a time limit, every retry stops
    ("0008", "app/services/sync.py", "    r = requests.get(url)", True),
    ("0008", "app/services/sync.py", "    r = requests.get(url, timeout=settings.http_timeout_seconds)", False),
    ("0008", "app/services/sync.py", "    client = httpx.AsyncClient(timeout=None)", True),
    ("0008", "app/services/sync.py", "    client = httpx.AsyncClient(timeout=settings.http_timeout_seconds)", False),
    ("0008", "app/services/sync.py", "@retry", True),
    ("0008", "app/services/sync.py", "@retry(stop=stop_after_attempt(3))", False),
]


@pytest.fixture(scope="module")
def project(tmp_path_factory) -> Path:
    """A throwaway project carrying the founding ADRs, exactly as a new project
    gets them — copied, not referenced, because that is how they will be used."""
    root = tmp_path_factory.mktemp("proj")
    shutil.copytree(ADRS, root / "adr")
    return root


def run_check(project: Path, rel: str, line: str) -> tuple[int, str]:
    f = project / rel
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(line + "\n", encoding="utf-8")
    p = subprocess.run(
        [sys.executable, str(CHECK)],
        input=json.dumps({"tool_input": {"file_path": str(f)}}),
        capture_output=True, text=True,
    )
    return p.returncode, p.stderr


@pytest.mark.parametrize("adr,rel,line,blocked", CASES,
                         ids=[f"{c[0]}-{'block' if c[3] else 'pass'}-{i}"
                              for i, c in enumerate(CASES)])
def test_enforcement(project, adr, rel, line, blocked):
    code, err = run_check(project, rel, line)
    if blocked:
        assert code != 0, f"ADR {adr} did NOT fire on a real violation:\n  {line}"
        assert adr in err, f"fired, but not from ADR {adr}:\n{err}"
    else:
        assert code == 0, (
            f"ADR {adr} fired on CORRECT code — this is the misfire class that "
            f"teaches an agent to route around the hook:\n  {line}\n{err}")


def test_every_adr_has_a_parseable_enforcement_block():
    import re
    for f in sorted(ADRS.glob("0*.md")):
        block = re.search(r"## Enforcement\s*\n+```json\n(.*?)\n```", f.read_text(), re.S)
        assert block, f"{f.name} has no enforcement block — it is a note, not a decision"
        d = json.loads(block.group(1))
        assert d.get("governs"), f"{f.name} governs nothing"
        assert d.get("forbid") or d.get("review"), f"{f.name} enforces nothing"
        for rule in d.get("forbid", []):
            re.compile(rule["pattern"])
            assert rule.get("message"), f"{f.name}: a forbid with no repair instruction"
