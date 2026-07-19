"""OpenVPN Connect preflight for API requests targeting test environments."""
from __future__ import annotations

import ipaddress
import ctypes
import os
import socket
import subprocess
import threading
import time
from ctypes import wintypes
from pathlib import Path
from urllib.parse import urlparse

import httpx
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.environment import Environment


class VpnConnectionError(RuntimeError):
    """Raised when a required test-environment VPN cannot be connected."""


_CONNECT_LOCK = threading.Lock()
_POLL_INTERVAL_SECONDS = 0.5
_FAKE_IP_NETWORK = ipaddress.ip_network("198.18.0.0/15")
_OPENVPN_WINDOW_TITLE = "OpenVPN Connect"
_CHROMIUM_RENDER_CLASS = "Chrome_RenderWidgetHostHWND"
_PROFILE_SWITCH_X = 49
_PROFILE_SWITCH_Y = 164
_WM_LBUTTONDOWN = 0x0201
_WM_LBUTTONUP = 0x0202
_MK_LBUTTON = 0x0001


def ensure_vpn_for_test_environment(
    db: Session,
    environment_id: int | None,
    target_url: str,
) -> dict:
    """Ensure the selected test environment is reachable through OpenVPN.

    Other environment types are deliberately ignored. When auto-connect is disabled,
    execution continues unchanged and reports that the preflight is disabled.
    """
    if not environment_id:
        return _status("not_required", required=False)

    environment = db.get(Environment, environment_id)
    if not environment or environment.env_type != "test":
        return _status("not_required", required=False)

    if not settings.openvpn_auto_connect_enabled:
        return _status("disabled", required=True)

    deadline = time.monotonic() + max(settings.openvpn_connect_timeout_seconds, 0.1)
    connected_now = False

    if not _openvpn_tunnel_connected():
        with _CONNECT_LOCK:
            # Another request may have completed the connection while this one waited.
            if not _openvpn_tunnel_connected():
                _start_openvpn_connect()
                if not _wait_for_openvpn_tunnel(deadline):
                    raise VpnConnectionError(
                        "OpenVPN 自动连接失败，OpenVPN 隧道未建立。"
                        "请确认客户端中最近使用的是项目 VPN，且配置无需交互式认证。"
                    )
                connected_now = True

    target = _wait_for_target(target_url, deadline)
    if not target:
        if _system_resolves_to_fake_ip(target_url):
            raise VpnConnectionError(
                "OpenVPN 隧道已建立，但目标域名仍被其他代理解析为 Fake-IP。"
                "请将 svc.elelive.cn 加入代理软件的 fake-ip-filter/直连规则后重试。"
            )
        raise VpnConnectionError(
            "OpenVPN 隧道已建立，但测试环境仍不可访问。"
            "请确认项目 VPN 路由包含目标服务地址。"
        )

    return _status(
        "connected",
        required=True,
        connected_now=connected_now,
        resolved_ip=target["resolved_ip"],
        dns_via_doh=target["dns_via_doh"],
    )


def _status(
    status: str,
    *,
    required: bool,
    connected_now: bool = False,
    resolved_ip: str | None = None,
    dns_via_doh: bool = False,
) -> dict:
    messages = {
        "not_required": "当前环境无需 OpenVPN",
        "disabled": "OpenVPN 自动连接未启用",
        "connected": "OpenVPN 已自动连接" if connected_now else "OpenVPN 已连接",
    }
    result = {
        "required": required,
        "status": status,
        "connected_now": connected_now,
        "message": messages[status],
    }
    if resolved_ip:
        result["resolved_ip"] = resolved_ip
        result["dns_via_doh"] = dns_via_doh
    return result


def _probe_target(target_url: str, timeout_seconds: float) -> dict | None:
    parsed = urlparse(target_url)
    if not parsed.hostname:
        return None
    port = parsed.port or (443 if parsed.scheme == "https" else 80)
    addresses = _resolve_system_addresses(parsed.hostname, port)
    real_addresses = [address for address in addresses if not _is_fake_proxy_ip(address)]
    dns_via_doh = not real_addresses and any(_is_fake_proxy_ip(address) for address in addresses)
    if dns_via_doh:
        real_addresses = _resolve_via_doh(parsed.hostname)

    for address in real_addresses:
        if _is_fake_proxy_ip(address):
            continue
        try:
            with socket.create_connection(
                (address, port),
                timeout=max(timeout_seconds, 0.1),
            ):
                return {"resolved_ip": address, "dns_via_doh": dns_via_doh}
        except OSError:
            continue
    return None


def _wait_for_openvpn_tunnel(deadline: float) -> bool:
    while time.monotonic() < deadline:
        if _openvpn_tunnel_connected():
            return True
        time.sleep(_POLL_INTERVAL_SECONDS)
    return False


def _wait_for_target(target_url: str, deadline: float) -> dict | None:
    while time.monotonic() < deadline:
        target = _probe_target(target_url, settings.openvpn_probe_timeout_seconds)
        if target:
            return target
        time.sleep(_POLL_INTERVAL_SECONDS)
    return None


def _openvpn_tunnel_connected() -> bool:
    if os.name != "nt":
        return False
    command = (
        "$adapter = Get-NetAdapter -IncludeHidden -ErrorAction SilentlyContinue | "
        "Where-Object { $_.Status -eq 'Up' -and $_.InterfaceDescription -match "
        "'OpenVPN|TAP-Windows Adapter|ovpn-dco' }; "
        "if ($adapter) { exit 0 } else { exit 1 }"
    )
    try:
        result = subprocess.run(
            ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", command],
            capture_output=True,
            timeout=5,
            check=False,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        return result.returncode == 0
    except (OSError, subprocess.SubprocessError):
        return False


def _resolve_system_addresses(hostname: str, port: int) -> list[str]:
    try:
        addresses = [
            item[4][0]
            for item in socket.getaddrinfo(hostname, port, type=socket.SOCK_STREAM)
        ]
    except OSError:
        return []
    return list(dict.fromkeys(addresses))


def _resolve_via_doh(hostname: str) -> list[str]:
    try:
        with httpx.Client(
            timeout=settings.openvpn_doh_timeout_seconds,
            follow_redirects=True,
        ) as client:
            response = client.get(
                settings.openvpn_doh_resolver_url,
                params={"name": hostname, "type": "A"},
                headers={"Accept": "application/dns-json"},
            )
            response.raise_for_status()
            answers = response.json().get("Answer", [])
    except (httpx.HTTPError, ValueError, TypeError):
        return []

    addresses = []
    for answer in answers:
        address = str(answer.get("data", "")) if answer.get("type") == 1 else ""
        try:
            ipaddress.ip_address(address)
        except ValueError:
            continue
        if not _is_fake_proxy_ip(address):
            addresses.append(address)
    return list(dict.fromkeys(addresses))


def _is_fake_proxy_ip(address: str) -> bool:
    try:
        return ipaddress.ip_address(address) in _FAKE_IP_NETWORK
    except ValueError:
        return False


def _system_resolves_to_fake_ip(target_url: str) -> bool:
    parsed = urlparse(target_url)
    if not parsed.hostname:
        return False
    port = parsed.port or (443 if parsed.scheme == "https" else 80)
    return any(
        _is_fake_proxy_ip(address)
        for address in _resolve_system_addresses(parsed.hostname, port)
    )


def _start_openvpn_connect() -> None:
    if os.name != "nt":
        raise VpnConnectionError("OpenVPN Connect 自动开关目前仅支持 Windows。")

    executable = Path(os.path.expandvars(settings.openvpn_connect_executable)).expanduser()
    if not executable.is_file():
        raise VpnConnectionError(
            f"未找到 OpenVPN Connect：{executable}。请在后端环境变量中配置 OPENVPN_CONNECT_EXECUTABLE。"
        )

    profile_directory = Path(
        os.path.expandvars(settings.openvpn_profile_directory)
    ).expanduser()
    profiles = list(profile_directory.glob("*.ovpn")) if profile_directory.is_dir() else []
    if len(profiles) != 1:
        raise VpnConnectionError(
            "OpenVPN Connect 中必须仅保留项目 VPN 配置，才能安全自动打开对应开关。"
            f"当前检测到 {len(profiles)} 个配置。"
        )

    window_handle = _find_openvpn_window()
    if window_handle is None:
        subprocess.Popen(
            [str(executable), "--minimize"],
            cwd=str(executable.parent),
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            close_fds=True,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        window_deadline = time.monotonic() + 10
        while window_handle is None and time.monotonic() < window_deadline:
            time.sleep(0.2)
            window_handle = _find_openvpn_window()

    if window_handle is None:
        raise VpnConnectionError("OpenVPN Connect 已启动，但未找到可控制的客户端窗口。")
    if not _click_openvpn_profile_switch(window_handle):
        raise VpnConnectionError("无法触发 OpenVPN Connect 中的项目 VPN 开关。")


def _find_openvpn_window() -> int | None:
    """Find OpenVPN Connect's Chromium window, including hidden/minimized windows."""
    if os.name != "nt":
        return None

    user32 = ctypes.WinDLL("user32", use_last_error=True)
    found: list[int] = []
    callback_type = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)

    def visit(window_handle, _lparam):
        length = user32.GetWindowTextLengthW(window_handle)
        if length <= 0:
            return True
        title = ctypes.create_unicode_buffer(length + 1)
        user32.GetWindowTextW(window_handle, title, len(title))
        if title.value == _OPENVPN_WINDOW_TITLE:
            found.append(int(window_handle))
            return False
        return True

    callback = callback_type(visit)
    user32.EnumWindows(callback, 0)
    return found[0] if found else None


def _click_openvpn_profile_switch(window_handle: int) -> bool:
    """Click the only saved profile switch without moving the user's mouse."""
    if os.name != "nt":
        return False

    user32 = ctypes.WinDLL("user32", use_last_error=True)
    child_handles: list[int] = []
    callback_type = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)

    def visit(child_handle, _lparam):
        class_name = ctypes.create_unicode_buffer(128)
        user32.GetClassNameW(child_handle, class_name, len(class_name))
        if class_name.value == _CHROMIUM_RENDER_CLASS:
            child_handles.append(int(child_handle))
            return False
        return True

    callback = callback_type(visit)
    user32.EnumChildWindows(window_handle, callback, 0)
    if not child_handles:
        return False

    render_handle = child_handles[0]
    coordinates = (_PROFILE_SWITCH_Y << 16) | (_PROFILE_SWITCH_X & 0xFFFF)
    pressed = user32.PostMessageW(
        render_handle,
        _WM_LBUTTONDOWN,
        _MK_LBUTTON,
        coordinates,
    )
    released = user32.PostMessageW(
        render_handle,
        _WM_LBUTTONUP,
        0,
        coordinates,
    )
    return bool(pressed and released)
