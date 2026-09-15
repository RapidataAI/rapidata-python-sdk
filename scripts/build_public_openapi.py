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

    serialized = json.dumps(spec).replace("rabbitdata.ch", "rapidata.ai")
    spec = json.loads(serialized)

    spec["servers"] = [{"url": "https://api.rapidata.ai/"}]
    info = spec.setdefault("info", {})
    info["title"] = "Rapidata API"
    info.setdefault(
        "description",
        "Public Rapidata API. Authentication uses OAuth 2.0 (OpenID Connect) — "
        "see https://docs.rapidata.ai/authentication/.",
    )
    return spec


def main() -> None:
    if len(sys.argv) != 2:
        print("Usage: python scripts/build_public_openapi.py <output.json>")
        raise SystemExit(2)
    out = Path(sys.argv[1])
    spec = build()
    out.write_text(json.dumps(spec), encoding="utf-8")
    print(
        f"Wrote {out} ({out.stat().st_size} bytes, {len(spec.get('paths', {}))} paths)"
    )


if __name__ == "__main__":
    main()
