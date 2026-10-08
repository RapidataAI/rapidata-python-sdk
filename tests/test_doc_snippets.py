import ast
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REPORTED_RULES = {"reportAttributeAccessIssue", "reportCallIssue", "reportArgumentType"}
BLOCK = re.compile(r"^( *)```(?:python|py)[^\n]*\n(.*?)^\1```", re.S | re.M)

# Names the docs use without defining them; typing them keeps their calls checked.
PREAMBLE = """\
from typing import Any
from rapidata import RapidataClient
from rapidata.rapidata_client.audience.rapidata_audience import RapidataAudience
from rapidata.rapidata_client.benchmark.rapidata_benchmark import RapidataBenchmark
from rapidata.rapidata_client.benchmark.leaderboard.rapidata_leaderboard import RapidataLeaderboard
def __any__(value: object) -> Any: return value
client = RapidataClient()
audience: RapidataAudience = __any__(None)
benchmark: RapidataBenchmark = __any__(None)
leaderboard: RapidataLeaderboard = __any__(None)
"""


def _untyped_results(code: str) -> str | None:
    """Wrap `.get_results()` in Any: flow items return a ranking-or-classify union.
    Returns None for blocks that aren't valid Python, such as sample output."""
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return None
    lines = code.split("\n")
    edits = []
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Call)
            and getattr(node.func, "attr", "") == "get_results"
        ):
            edits.append((node.end_lineno, node.end_col_offset, ")"))
            edits.append((node.lineno, node.col_offset, "__any__("))
    for line, col, text in sorted(edits, reverse=True):
        row = lines[line - 1]
        col = len(row.encode()[:col].decode())
        lines[line - 1] = row[:col] + text + row[col:]
    return "\n".join(lines)


def test_doc_examples_match_the_sdk(tmp_path):
    line_map = {}
    for md in sorted((ROOT / "docs").rglob("*.md")):
        target = tmp_path / (re.sub(r"\W", "_", str(md.relative_to(ROOT))) + ".py")
        source, generated = PREAMBLE, PREAMBLE.count("\n") + 1
        text = md.read_text(encoding="utf-8")
        for match in BLOCK.finditer(text):
            indent = len(match.group(1))
            code = _untyped_results(
                "\n".join(line[indent:] for line in match.group(2).split("\n"))
            )
            if code is None:
                continue
            first = text.count("\n", 0, match.start(2)) + 1
            for n in range(code.count("\n") + 1):
                line_map[(target.name, generated + n)] = (
                    md.relative_to(ROOT),
                    first + n,
                )
            source += code + "\n"
            generated += code.count("\n") + 1
        target.write_text(source, encoding="utf-8")

    (tmp_path / "pyrightconfig.json").write_text(
        json.dumps({"extraPaths": [str(ROOT / "src")]})
    )
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "pyright",
            "--outputjson",
            "--pythonpath",
            sys.executable,
            str(tmp_path),
        ],
        capture_output=True,
        text=True,
    )
    problems = []
    for diag in json.loads(result.stdout)["generalDiagnostics"]:
        key = (Path(diag["file"]).name, diag["range"]["start"]["line"] + 1)
        # Without the preamble every SDK type is Unknown and nothing gets checked.
        assert key in line_map or diag["severity"] != "error", diag["message"]
        rule = diag.get("rule", "")
        if rule in REPORTED_RULES or (
            rule == "reportMissingImports" and '"rapidata' in diag["message"]
        ):
            path, line = line_map[key]
            problems.append(f"{path}:{line}: {diag['message'].splitlines()[0]}")
    assert not problems, "Doc examples that break against this SDK:\n" + "\n".join(
        problems
    )
