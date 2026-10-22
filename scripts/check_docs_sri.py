from __future__ import annotations

import base64
import hashlib
import io
import json
import re
import sys
import tarfile
import urllib.request
from pathlib import Path

ANALYTICS = Path(__file__).resolve().parent.parent / "docs" / "js" / "analytics.js"
CDN_URL = re.compile(r'"(https://cdn\.jsdelivr\.net/[^"]+)"')
ASSET = re.compile(
    r'url: "https://cdn\.jsdelivr\.net/npm/(?P<package>[^@"]+)@(?P<version>[^/"]+)/(?P<path>[^"]+)",\s*'
    r'integrity: "(?P<integrity>sha384-[^"]+)"'
)


def fetch(url: str) -> bytes:
    with urllib.request.urlopen(url, timeout=60) as response:
        return response.read()


def sri(algorithm: str, data: bytes) -> str:
    digest = hashlib.new(algorithm, data).digest()
    return f"{algorithm}-{base64.b64encode(digest).decode()}"


def check(package: str, version: str, path: str, integrity: str) -> str | None:
    dist = json.loads(fetch(f"https://registry.npmjs.org/{package}/{version}"))["dist"]
    tarball = fetch(dist["tarball"])
    if sri("sha512", tarball) != dist["integrity"]:
        return f"{package}@{version}: tarball does not match the npm registry integrity"
    with tarfile.open(fileobj=io.BytesIO(tarball)) as archive:
        member = archive.extractfile(f"package/{path}")
        if member is None:
            return f"{package}@{version}: {path} is not in the published package"
        expected = sri("sha384", member.read())
    if expected != integrity:
        return f"{package}@{version}/{path}: npm publishes {expected}, analytics.js pins {integrity}"
    return None


def main() -> int:
    source = ANALYTICS.read_text(encoding="utf-8")
    assets = [match.groupdict() for match in ASSET.finditer(source)]
    if len(assets) != len(CDN_URL.findall(source)):
        print("Every jsDelivr URL in analytics.js needs a pinned sha384 integrity")
        return 1
    errors = [error for asset in assets if (error := check(**asset))]
    for error in errors:
        print(error)
    if not errors:
        print(f"{len(assets)} pinned assets match their npm packages")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
