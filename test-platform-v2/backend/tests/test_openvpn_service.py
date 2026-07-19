"""OpenVPN auto-connect preflight tests."""
from __future__ import annotations

import socket
from unittest.mock import MagicMock, Mock

import pytest


def _add_environment(db_session, *, env_id: int, env_type: str):
    from app.models.environment import Environment

    environment = Environment(
        id=env_id,
        project_id=1,
        name=f"{env_type}-environment",
        env_type=env_type,
        base_url="https://test.example.com",
    )
    db_session.add(environment)
    db_session.commit()
    return environment


def test_non_test_environment_does_not_start_openvpn(db_session, monkeypatch):
    from app.core.config import settings
    from app.services import openvpn_service

    environment = _add_environment(db_session, env_id=1, env_type="staging")
    start = Mock()
    monkeypatch.setattr(settings, "openvpn_auto_connect_enabled", True)
    monkeypatch.setattr(openvpn_service, "_start_openvpn_connect", start)

    result = openvpn_service.ensure_vpn_for_test_environment(
        db_session, environment.id, "https://staging.example.com/health",
    )

    assert result["status"] == "not_required"
    start.assert_not_called()


def test_active_openvpn_tunnel_reuses_connection(db_session, monkeypatch):
    from app.core.config import settings
    from app.services import openvpn_service

    environment = _add_environment(db_session, env_id=2, env_type="test")
    start = Mock()
    monkeypatch.setattr(settings, "openvpn_auto_connect_enabled", True)
    monkeypatch.setattr(openvpn_service, "_openvpn_tunnel_connected", lambda: True)
    monkeypatch.setattr(openvpn_service, "_wait_for_target", lambda *_args, **_kwargs: {
        "resolved_ip": "192.168.50.170",
        "dns_via_doh": True,
    })
    monkeypatch.setattr(openvpn_service, "_start_openvpn_connect", start)

    result = openvpn_service.ensure_vpn_for_test_environment(
        db_session, environment.id, "https://test.example.com/health",
    )

    assert result["status"] == "connected"
    assert result["connected_now"] is False
    assert result["resolved_ip"] == "192.168.50.170"
    start.assert_not_called()


def test_other_tunnel_tcp_reachability_does_not_count_as_openvpn(db_session, monkeypatch):
    from app.core.config import settings
    from app.services import openvpn_service

    environment = _add_environment(db_session, env_id=3, env_type="test")
    start = Mock()
    monkeypatch.setattr(settings, "openvpn_auto_connect_enabled", True)
    monkeypatch.setattr(openvpn_service, "_openvpn_tunnel_connected", lambda: False)
    monkeypatch.setattr(openvpn_service, "_start_openvpn_connect", start)
    monkeypatch.setattr(openvpn_service, "_wait_for_openvpn_tunnel", lambda *_args, **_kwargs: False)

    with pytest.raises(openvpn_service.VpnConnectionError, match="隧道未建立"):
        openvpn_service.ensure_vpn_for_test_environment(
            db_session, environment.id, "https://test.example.com/health",
        )

    start.assert_called_once_with()


def test_disconnected_openvpn_starts_and_waits_for_tunnel_and_target(db_session, monkeypatch):
    from app.core.config import settings
    from app.services import openvpn_service

    environment = _add_environment(db_session, env_id=4, env_type="test")
    monkeypatch.setattr(settings, "openvpn_auto_connect_enabled", True)
    monkeypatch.setattr(openvpn_service, "_openvpn_tunnel_connected", lambda: False)
    start = Mock()
    monkeypatch.setattr(openvpn_service, "_start_openvpn_connect", start)
    monkeypatch.setattr(openvpn_service, "_wait_for_openvpn_tunnel", lambda *_args, **_kwargs: True)
    monkeypatch.setattr(openvpn_service, "_wait_for_target", lambda *_args, **_kwargs: {
        "resolved_ip": "192.168.50.170",
        "dns_via_doh": True,
    })

    result = openvpn_service.ensure_vpn_for_test_environment(
        db_session, environment.id, "https://test.example.com/health",
    )

    assert result["status"] == "connected"
    assert result["connected_now"] is True
    assert result["dns_via_doh"] is True
    start.assert_called_once_with()


def test_fake_ip_is_replaced_with_real_doh_address(monkeypatch):
    from app.services import openvpn_service

    monkeypatch.setattr(socket, "getaddrinfo", lambda *_args, **_kwargs: [
        (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("198.18.0.146", 80)),
    ])
    monkeypatch.setattr(openvpn_service, "_resolve_via_doh", lambda _host: ["192.168.50.170"])
    connection = MagicMock()
    monkeypatch.setattr(socket, "create_connection", Mock(return_value=connection))

    result = openvpn_service._probe_target(
        "http://camel-api-gateway05.svc.elelive.cn/health",
        timeout_seconds=1,
    )

    assert result == {
        "resolved_ip": "192.168.50.170",
        "dns_via_doh": True,
    }
    socket.create_connection.assert_called_once_with(("192.168.50.170", 80), timeout=1)


def test_start_openvpn_connect_clicks_single_saved_profile_without_shell(tmp_path, monkeypatch):
    from app.core.config import settings
    from app.services import openvpn_service

    executable = tmp_path / "OpenVPNConnect.exe"
    executable.write_bytes(b"")
    profile_directory = tmp_path / "profiles"
    profile_directory.mkdir()
    (profile_directory / "project.ovpn").write_text("client\n", encoding="utf-8")
    popen = Mock()
    monkeypatch.setattr(settings, "openvpn_connect_executable", str(executable))
    monkeypatch.setattr(settings, "openvpn_profile_directory", str(profile_directory))
    monkeypatch.setattr(openvpn_service.subprocess, "Popen", popen)
    monkeypatch.setattr(openvpn_service, "_find_openvpn_window", Mock(side_effect=[None, 123]))
    click = Mock(return_value=True)
    monkeypatch.setattr(openvpn_service, "_click_openvpn_profile_switch", click)

    openvpn_service._start_openvpn_connect()

    popen.assert_called_once_with(
        [str(executable), "--minimize"],
        cwd=str(executable.parent),
        stdin=openvpn_service.subprocess.DEVNULL,
        stdout=openvpn_service.subprocess.DEVNULL,
        stderr=openvpn_service.subprocess.DEVNULL,
        close_fds=True,
        creationflags=openvpn_service.subprocess.CREATE_NO_WINDOW,
    )
    click.assert_called_once_with(123)


def test_start_openvpn_connect_rejects_ambiguous_saved_profiles(tmp_path, monkeypatch):
    from app.core.config import settings
    from app.services import openvpn_service

    executable = tmp_path / "OpenVPNConnect.exe"
    executable.write_bytes(b"")
    profile_directory = tmp_path / "profiles"
    profile_directory.mkdir()
    (profile_directory / "first.ovpn").write_text("client\n", encoding="utf-8")
    (profile_directory / "second.ovpn").write_text("client\n", encoding="utf-8")
    monkeypatch.setattr(settings, "openvpn_connect_executable", str(executable))
    monkeypatch.setattr(settings, "openvpn_profile_directory", str(profile_directory))

    with pytest.raises(openvpn_service.VpnConnectionError, match="仅保留项目 VPN"):
        openvpn_service._start_openvpn_connect()
