import stat
import threading
from datetime import datetime, timezone
from pathlib import Path

import pytest

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
