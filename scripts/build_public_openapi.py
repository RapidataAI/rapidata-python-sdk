"""Produce the public OpenAPI document served at docs.rapidata.ai/openapi.json.

The combined spec under ``openapi/schemas/`` is the contract the SDK is generated
from, but it carries the internal ``rabbitdata.ch`` host and an inaccurate title.
Rewrite those to the public ``rapidata.ai`` host (which already serves the same
per-service specs and OIDC discovery document) so agents get an accurate surface.

Usage: python scripts/build_public_openapi.py <output.json>
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

SOURCE = (
    Path(__file__).resolve().parent.parent
    / "openapi"
    / "schemas"
    / "rapidata.filtered.openapi.json"
)


def build() -> dict:
    spec = json.loads(SOURCE.read_text(encoding="utf-8"))

    # The internal build host is the only thing standing between this and the
    # live public spec at api.rapidata.ai — rewrite both the server and the
    # OIDC discovery URL in the security scheme.
    serialized = json.dumps(spec).replace("rabbitdata.ch", "rapidata.ai")
    spec = json.loads(serialized)

    spec["servers"] = [{"url": "https://api.rapidata.ai/"}]
    info = spec.setdefault("info", {})
    info["title"] = "Rapidata API"
    info.setdefault(
        "description",
        "Public Rapidata API. Authentication uses OAuth 2.0 (OpenID Connect) — "
        "see https://docs.rapidata.ai/latest/authentication/.",
    )
    return spec


def main() -> None:
    if len(sys.argv) != 2:
        print(__doc__)
        raise SystemExit(2)
    out = Path(sys.argv[1])
    spec = build()
    out.write_text(json.dumps(spec), encoding="utf-8")
    print(
        f"Wrote {out} ({out.stat().st_size} bytes, {len(spec.get('paths', {}))} paths)"
    )


if __name__ == "__main__":
    main()
