"""Default molecule test suite for ansible-role-docker_phpbb."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from testinfra.host import Host


def test_compose_directory_exists(host: Host) -> None:
    d = host.file("/opt/phpbb")
    assert d.exists
    assert d.is_directory


def test_compose_directory_mode(host: Host) -> None:
    d = host.file("/opt/phpbb")
    assert d.mode == 0o750


def test_compose_file_exists(host: Host) -> None:
    f = host.file("/opt/phpbb/compose.yml")
    assert f.exists
    assert f.is_file


def test_compose_file_mode(host: Host) -> None:
    f = host.file("/opt/phpbb/compose.yml")
    assert f.mode == 0o640


def test_env_secrets_exists(host: Host) -> None:
    f = host.file("/opt/phpbb/.env.secrets")
    assert f.exists
    assert f.is_file


def test_env_secrets_mode(host: Host) -> None:
    """Secrets file must be mode 0600 — not world- or group-readable."""
    f = host.file("/opt/phpbb/.env.secrets")
    assert f.mode == 0o600


def test_compose_contains_mysql_service(host: Host) -> None:
    f = host.file("/opt/phpbb/compose.yml")
    assert "phpbb-mysql" in f.content_string


def test_compose_contains_phpbb_service(host: Host) -> None:
    f = host.file("/opt/phpbb/compose.yml")
    assert 'container_name: "phpbb"' in f.content_string


def test_compose_network_is_external(host: Host) -> None:
    f = host.file("/opt/phpbb/compose.yml")
    assert "external: true" in f.content_string


def test_compose_domain_rendered(host: Host) -> None:
    f = host.file("/opt/phpbb/compose.yml")
    assert "phpbb.molecule.test" in f.content_string
