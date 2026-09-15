from __future__ import annotations

import argparse
import html
import json
import shutil
from pathlib import Path

SITE_URL = "https://docs.rapidata.ai"
ALIASES = ("latest", "3.x")
RESERVED = {*ALIASES, "2.x", ".git"}
RENAMED = {
    "starting_page/index.html": "index.html",
    **{
        f"examples/{task}_order/index.html": f"examples/{task}_job/index.html"
        for task in (
            "classify",
            "compare",
            "draw",
            "free_text",
            "locate",
            "ranking",
            "select_words",
        )
    },
    "improve_order_quality/index.html": "audiences/index.html",
}


def pages(directory: Path) -> set[Path]:
    return {
        path.relative_to(directory)
        for path in directory.rglob("*.html")
        if path.relative_to(directory).parts[0] not in RESERVED
        and path.name != "404.html"
    }


def page_url(path: Path) -> str:
    url = "/" + path.as_posix()
    return url.removesuffix("index.html") if path.name == "index.html" else url


def redirect(destination: Path) -> str:
    url = page_url(destination)
    escaped = html.escape(url, quote=True)
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>Documentation moved</title>
  <link rel="canonical" href="{SITE_URL}{escaped}">
  <script>window.location.replace({json.dumps(url)} + window.location.search + window.location.hash);</script>
  <noscript><meta http-equiv="refresh" content="0; url={escaped}"></noscript>
</head>
<body><p>This documentation has moved to <a href="{escaped}">{escaped}</a>.</p></body>
</html>
"""


def prepare(site: Path, previous: Path, root_files: Path) -> None:
    if not (site / "quickstart/index.html").is_file():
        raise ValueError("Build the current documentation before preparing the site")
    if any((site / name).exists() for name in RESERVED):
        raise ValueError(
            "Use a clean MkDocs build, without archived versions or aliases"
        )
    if not (previous / "2.x/index.html").is_file():
        raise ValueError("The published 2.x archive is required before deployment")

    for name in ("robots.txt", "llms.txt"):
        shutil.copyfile(root_files / name, site / name)
    shutil.copytree(root_files / "developers", site / "developers", dirs_exist_ok=True)
    shutil.copyfile(root_files.parent / "CNAME", site / "CNAME")
    (site / ".nojekyll").touch()

    current = pages(site)
    historical = pages(previous)
    for alias in ALIASES:
        historical |= pages(previous / alias)

    for page in sorted(current | historical | {Path(p) for p in RENAMED}):
        target = Path(RENAMED.get(page.as_posix(), page.as_posix()))
        if target not in current:
            target = Path("migration/index.html")
        if not (site / target).is_file():
            raise ValueError(f"Missing redirect destination: {target}")
        content = redirect(target)
        if page not in current:
            output = site / page
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_text(content, encoding="utf-8")
        for alias in ALIASES:
            output = site / alias / page
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_text(content, encoding="utf-8")

    # Machine-readable links need their content; HTML redirects cannot replace it.
    for source in list(site.rglob("*.md")) + [
        site / "llms.txt",
        site / "llms-full.txt",
    ]:
        for alias in ALIASES:
            output = site / alias / source.relative_to(site)
            output.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, output)

    shutil.copytree(previous / "2.x", site / "2.x")
    (site / "versions.json").write_text(
        json.dumps(
            [
                {"version": "3.x", "title": "Current", "aliases": ["latest"]},
                {"version": "2.x", "title": "2.x (legacy)", "aliases": []},
            ]
        )
        + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--site", type=Path, required=True)
    parser.add_argument("--previous", type=Path, required=True)
    args = parser.parse_args()
    prepare(
        args.site, args.previous, Path(__file__).resolve().parent.parent / "site_root"
    )
