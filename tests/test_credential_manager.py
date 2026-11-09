import base64
import json
import stat
import threading
import webbrowser
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import pytest
import requests

from rapidata.service.credential_manager import ClientCredential, CredentialManager


@pytest.fixture
def manager(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> CredentialManager:
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: tmp_path))
    return CredentialManager(endpoint="https://api.rapidata.ai")


def _credential() -> ClientCredential:
    now = datetime.now(timezone.utc)
    return ClientCredential(
        display_name="test",
        client_id="id",
        client_secret="secret",
        endpoint="https://api.rapidata.ai",
        created_at=now,
        last_used=now,
    )


def test_concurrent_writes_all_succeed(manager: CredentialManager):
    credentials = {manager.endpoint: [_credential()]}
    errors: list[BaseException] = []
    start = threading.Barrier(16)

    def write():
        start.wait()
        try:
            for _ in range(20):
                manager._write_credentials(credentials)
        except BaseException as e:
            errors.append(e)

    threads = [threading.Thread(target=write) for _ in range(16)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert errors == []
    assert manager._read_credentials()[manager.endpoint][0].client_id == "id"
    assert list(manager.config_dir.glob("*.tmp")) == []


def test_written_file_is_owner_only(manager: CredentialManager):
    manager._write_credentials({manager.endpoint: [_credential()]})

    assert stat.S_IMODE(manager.config_path.stat().st_mode) == 0o600


def _jwt(claims: dict) -> str:
    def part(data: dict) -> str:
        return base64.urlsafe_b64encode(json.dumps(data).encode()).decode().rstrip("=")

    return f"{part({'alg': 'none'})}.{part(claims)}.sig"


class FakeIdentity:
    """Bridge-token login where the browser lands in `token_org`, as identity would."""

    def __init__(
        self,
        monkeypatch: pytest.MonkeyPatch,
        token_org: str | None,
        client_org: str | None = None,
    ):
        self.token_org = token_org
        self.client_org = client_org
        self.opened: list[str] = []
        self.created = 0
        monkeypatch.setattr(webbrowser, "open", self._open)
        monkeypatch.setattr(requests, "post", self._post)
        monkeypatch.setattr(requests, "get", self._get)

    def _open(self, url: str) -> bool:
        self.opened.append(url)
        return True

    def _post(self, url: str, **kwargs):
        if "/identity/bridge-token" in url:
            return _Response({"readKey": "read", "writeKey": "write"})
        self.created += 1
        organization = self.client_org or self.token_org
        return _Response(
            {
                "clientId": f"client-{self.created}",
                "clientSecret": "s",
                "organizationId": organization,
                "organizationName": f"{organization} name",
            }
        )

    def _get(self, url: str, **kwargs):
        claims = {"org": self.token_org} if self.token_org else {}
        return _Response({"accessToken": _jwt(claims)})


class _Response:
    ok = True
    status_code = 200

    def __init__(self, body: dict):
        self._body = body

    def json(self) -> dict:
        return self._body

    def raise_for_status(self) -> None:
        pass


def _login_query(url: str) -> dict[str, list[str]]:
    return parse_qs(urlparse(url).query)


@pytest.fixture
def home(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: tmp_path))
    return tmp_path


def test_organization_id_reaches_the_login_url(
    home: Path, monkeypatch: pytest.MonkeyPatch
):
    identity = FakeIdentity(monkeypatch, token_org="org_a")
    manager = CredentialManager(
        endpoint="https://auth.rapidata.ai", organization_id="org_a"
    )

    credential = manager.get_client_credentials()

    assert _login_query(identity.opened[0])["organization"] == ["org_a"]
    assert credential is not None and credential.organization_id == "org_a"


def test_login_url_has_no_organization_when_none_is_pinned(
    home: Path, monkeypatch: pytest.MonkeyPatch
):
    identity = FakeIdentity(monkeypatch, token_org="org_active")

    credential = CredentialManager(
        endpoint="https://auth.rapidata.ai"
    ).get_client_credentials()

    assert "organization" not in _login_query(identity.opened[0])
    assert credential is not None and credential.organization_id == "org_active"


def test_two_organizations_keep_separate_credentials(
    home: Path, monkeypatch: pytest.MonkeyPatch
):
    identity = FakeIdentity(monkeypatch, token_org="org_a")
    a = CredentialManager(endpoint="https://auth.rapidata.ai", organization_id="org_a")
    first_a = a.get_client_credentials()
    identity.token_org = "org_b"
    b = CredentialManager(endpoint="https://auth.rapidata.ai", organization_id="org_b")
    first_b = b.get_client_credentials()

    assert first_a is not None and first_b is not None
    assert first_a.client_id != first_b.client_id
    assert a.get_client_credentials().client_id == first_a.client_id  # type: ignore[union-attr]
    assert b.get_client_credentials().client_id == first_b.client_id  # type: ignore[union-attr]
    assert identity.created == 2

    b.reset_credentials()
    assert a.stored_credential() is not None
    assert b.stored_credential() is None


def test_login_landing_in_another_organization_stores_nothing(
    home: Path, monkeypatch: pytest.MonkeyPatch
):
    identity = FakeIdentity(monkeypatch, token_org="org_other")
    manager = CredentialManager(
        endpoint="https://auth.rapidata.ai", organization_id="org_a"
    )

    with pytest.raises(ValueError, match="org_other"):
        manager.get_client_credentials()

    assert identity.created == 0
    assert manager.stored_credential() is None


def test_legacy_credentials_file_still_loads(
    home: Path, monkeypatch: pytest.MonkeyPatch
):
    legacy = {
        "https://auth.rapidata.ai": [
            {
                "display_name": "host - Python API Client",
                "client_id": "legacy-id",
                "client_secret": "legacy-secret",
                "endpoint": "https://auth.rapidata.ai",
                "created_at": "2025-01-01T00:00:00Z",
                "last_used": "2025-01-01T00:00:00Z",
            }
        ]
    }
    config = home / ".config" / "rapidata"
    config.mkdir(parents=True)
    (config / "credentials.json").write_text(json.dumps(legacy))
    identity = FakeIdentity(monkeypatch, token_org="org_a")

    unpinned = CredentialManager(
        endpoint="https://auth.rapidata.ai"
    ).get_client_credentials()
    assert unpinned is not None and unpinned.client_id == "legacy-id"
    assert identity.opened == []

    pinned = CredentialManager(
        endpoint="https://auth.rapidata.ai", organization_id="org_a"
    )
    assert pinned.stored_credential() is None
    assert pinned.get_client_credentials().client_id == "client-1"  # type: ignore[union-attr]
    stored = json.loads((config / "credentials.json").read_text())[
        "https://auth.rapidata.ai"
    ]
    assert {c["client_id"] for c in stored} == {"legacy-id", "client-1"}


def test_stored_organization_comes_from_the_created_client(
    home: Path, monkeypatch: pytest.MonkeyPatch
):
    FakeIdentity(monkeypatch, token_org=None, client_org="org_from_client")

    credential = CredentialManager(
        endpoint="https://auth.rapidata.ai"
    ).get_client_credentials()

    assert credential is not None and credential.organization_id == "org_from_client"
