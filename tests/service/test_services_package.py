"""Tests that keep ``rapidata.service.services`` importable.

``openapi_service`` reaches every backend service through a lazy
``from rapidata.service.services.<name>_service import ...``, and that import
runs the package ``__init__`` first. So a single stale name in ``__init__``
breaks *every* API call in the published wheel, not just the service that was
removed — which is how 3.21.0 shipped with a dead ``pipeline_service`` import
and raised ``ModuleNotFoundError`` on any call.
"""

from __future__ import annotations

import importlib
from pathlib import Path

import pytest

import rapidata.service.services as services_package


def _service_modules() -> list[str]:
    package_dir = Path(services_package.__file__).parent
    return sorted(p.stem for p in package_dir.glob("*_service.py"))


class TestServicesPackage:
    def test_every_exported_name_is_resolvable(self):
        """A name left in ``__all__`` after its module was deleted is the failure mode."""
        for name in services_package.__all__:
            assert (
                getattr(services_package, name, None) is not None
            ), f"{name} is exported but not bound"

    @pytest.mark.parametrize("module_name", _service_modules())
    def test_every_service_module_is_exported(self, module_name: str):
        """Keeps ``__all__`` in sync with the modules actually on disk."""
        module = importlib.import_module(f"rapidata.service.services.{module_name}")
        expected = "".join(part.capitalize() for part in module_name.split("_"))

        assert hasattr(module, expected), f"{module_name} has no {expected}"
        assert (
            expected in services_package.__all__
        ), f"{expected} is missing from rapidata.service.services.__all__"
