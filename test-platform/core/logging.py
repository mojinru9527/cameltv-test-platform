"""统一 rich 日志/控制台。各工具共用，保证输出风格一致。

Windows 控制台默认 GBK/cp936，rich 的旧版 Windows 渲染器会在遇到非 GBK 字符
（box 线、glyph、部分 emoji）时抛 UnicodeEncodeError。这里把 stdout/stderr 统一
重配为 UTF-8 并禁用 legacy 渲染，保证任何代码页下都不崩。
"""
from __future__ import annotations

import sys

from rich.console import Console

for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8")  # type: ignore[union-attr]
    except Exception:
        pass

console = Console(legacy_windows=False)


def info(msg: str) -> None:
    console.print(f"[cyan]›[/cyan] {msg}")


def ok(msg: str) -> None:
    console.print(f"[green]✓[/green] {msg}")


def warn(msg: str) -> None:
    console.print(f"[yellow]![/yellow] {msg}")


def err(msg: str) -> None:
    console.print(f"[red]✗[/red] {msg}")


def rule(title: str) -> None:
    console.rule(f"[bold]{title}[/bold]")
