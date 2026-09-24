from pathlib import Path

import pytest

from scripts.prepare_docs_site import prepare


def write(directory: Path, name: str, content: str = "current") -> Path:
    path = directory / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path


def build_site(directory: Path) -> Path:
    for name in (
        "index.html",
        "quickstart/index.html",
        "migration/index.html",
        "audiences/index.html",
        "examples/compare_job/index.html",
        "assets/stylesheets/main.css",
        "llms-full.txt",
        "quickstart.md",
        "sitemap.xml",
    ):
        write(directory, name)
    return directory


@pytest.fixture
def root_files(tmp_path):
    directory = tmp_path / "repo/site_root"
    for name in ("robots.txt", "llms.txt", "developers/index.html"):
        write(directory, name)
    write(directory, "README.md", "not public")
    write(directory.parent, "CNAME", "docs.rapidata.ai")
    return directory


def test_migrates_published_pages_and_retires_archive(tmp_path, root_files):
    previous = tmp_path / "published"
    write(previous, "2.x/index.html", "legacy homepage")
    write(previous, "2.x/assets/style.css", "legacy styles")
    write(previous, "2.x/reference/order/index.html", "legacy order API")
    write(previous, "2.x/sitemap.xml", "legacy sitemap")
    write(previous, "versions.json", "legacy selector")
    write(previous, "quickstart/index.html", "obsolete instructions")
    write(previous, "examples/compare_order/index.html", "obsolete example")
    write(previous, "3.x/reference/removed/index.html", "obsolete API")
    write(previous, "assets/obsolete.js", "obsolete asset")
    (previous / "latest").symlink_to("3.x", target_is_directory=True)
    site = build_site(tmp_path / "site")

    prepare(site, previous, root_files)

    for prefix in ("", "latest/", "3.x/"):
        comparison = (site / prefix / "examples/compare_order/index.html").read_text()
        assert 'href="/examples/compare_job/"' in comparison
        removed = (site / prefix / "reference/removed/index.html").read_text()
        assert 'href="/migration/"' in removed
        home = (site / prefix / "starting_page/index.html").read_text()
        assert 'href="/"' in home
    for prefix in ("latest", "3.x"):
        quickstart = (site / prefix / "quickstart/index.html").read_text()
        assert 'href="https://docs.rapidata.ai/quickstart/"' in quickstart
        assert "window.location.search + window.location.hash" in quickstart
        assert '<noscript><meta http-equiv="refresh"' in quickstart
        assert (site / prefix / "quickstart.md").read_text() == "current"
        assert (site / prefix / "llms-full.txt").read_text() == "current"
        assert (site / prefix / "assets/stylesheets/main.css").read_text() == "current"
        assert (site / prefix / "index.html").read_text() != "current"
        assert not (site / prefix).is_symlink()
    assert (site / "index.html").read_text() == "current"
    assert (site / "quickstart/index.html").read_text() == "current"
    assert (site / "sitemap.xml").read_text() == "current"
    for page in ("2.x/index.html", "2.x/reference/order/index.html"):
        legacy = (site / page).read_text()
        assert 'href="https://docs.rapidata.ai/"' in legacy
        assert '<meta name="robots" content="noindex">' in legacy
    assert not (site / "2.x/assets/style.css").exists()
    assert not (site / "2.x/sitemap.xml").exists()
    assert not (site / "versions.json").exists()
    assert (site / "CNAME").read_text() == "docs.rapidata.ai"
    assert (site / ".nojekyll").is_file()
    assert not (site / "README.md").exists()
    assert not (site / "assets/obsolete.js").exists()

    next_site = build_site(tmp_path / "next-site")
    prepare(next_site, site, root_files)
    assert (next_site / "3.x/reference/removed/index.html").read_text() == removed
    assert (next_site / "latest/quickstart.md").read_text() == "current"
    assert not (next_site / "latest/latest").exists()
    assert (next_site / "2.x/reference/order/index.html").read_text() == legacy


def test_publishes_without_legacy_archive(tmp_path, root_files):
    site = build_site(tmp_path / "site")
    prepare(site, tmp_path / "missing", root_files)
    assert 'href="https://docs.rapidata.ai/"' in (site / "2.x/index.html").read_text()


def test_existing_alias_blocks_reusing_dirty_build(tmp_path, root_files):
    previous = tmp_path / "published"
    write(previous, "2.x/index.html")
    site = build_site(tmp_path / "site")
    write(site, "3.x/index.html")
    with pytest.raises(ValueError, match="clean MkDocs build"):
        prepare(site, previous, root_files)
