# Documentation publishing

Current documentation is built with MkDocs at `https://docs.rapidata.ai/`.
The overview is `docs/index.md`; `starting_page/` remains a redirect.

## Build and publish

1. Run `uv run --group docs mkdocs build`.
2. Check out the published `gh-pages` branch into a separate directory.
3. Run `uv run python scripts/prepare_docs_site.py --site site --previous <published-directory>`.
4. Run `uv run python scripts/build_public_openapi.py site/openapi.json`.
5. Publish the complete `site/` output, replacing the previous site contents.

The **Deploy Documentation** workflow validates this build on pull requests and
publishes it when manually dispatched from `main`. Merging alone does not deploy.
The workflow retains GitHub Pages' existing `gh-pages` branch configuration.
It explicitly requests a Pages build after pushing and waits for publication.

## Compatibility

The publisher copies the existing `2.x/` archive unchanged and retains
`versions.json` for its version selector. It refuses to publish without the archive.
Remove this requirement deliberately when retiring 2.x.

`latest/` and `3.x/` contain HTML redirects to current root pages. Redirects preserve
query strings and fragments in JavaScript, with a no-JavaScript fallback link and
refresh. They are not HTTP 301/308 responses. Renamed examples redirect to their
current equivalents; removed pages point to migration guidance.

The publisher inventories both the previous site and the new build, keeping old
redirect paths across deployments. It copies current Markdown and `llms*.txt`
content under the old prefixes for clients that cannot follow HTML redirects.

## Root files

| File | Source |
|---|---|
| Homepage, sitemap, search index, `llms-full.txt` | Current MkDocs build |
| `robots.txt`, `llms.txt`, `developers/` | Curated files in this directory |
| `openapi.json` | `scripts/build_public_openapi.py` |
| `CNAME` | Repository root |

Curated links use root URLs. `README.md` is never copied to the published site.
