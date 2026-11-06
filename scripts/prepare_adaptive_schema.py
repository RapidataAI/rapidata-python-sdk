from __future__ import annotations

import json
import sys
from pathlib import Path

from check_adaptive_stopping_contract import referee_unions


def main() -> None:
    path = Path(sys.argv[1])
    document = json.loads(path.read_text())
    for name, discriminator in referee_unions(document).items():
        schema = document["components"]["schemas"][name]
        schema["x-rapidata-adaptive-stopping-union"] = True
        schema["x-rapidata-adaptive-stopping-discriminator"] = discriminator
    path.write_text(json.dumps(document, indent=2) + "\n")


if __name__ == "__main__":
    main()
