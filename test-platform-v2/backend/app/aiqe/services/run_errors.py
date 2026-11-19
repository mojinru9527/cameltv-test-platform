"""Run/输出解析错误类型（独立模块，避免 RunContext 与 OutputSanitizer 循环依赖）。"""
from __future__ import annotations

VARIABLE_NOT_FOUND = "VARIABLE_NOT_FOUND"
VARIABLE_NOT_ANCESTOR = "VARIABLE_NOT_ANCESTOR"
SECRET_UNAVAILABLE = "SECRET_UNAVAILABLE"
FIXTURE_NOT_FOUND = "FIXTURE_NOT_FOUND"
OUTPUT_SCHEMA_MISMATCH = "OUTPUT_SCHEMA_MISMATCH"


class VariableResolutionError(ValueError):
    """变量引用无法解析；`code` 用于 Run/Node 错误分类。"""

    def __init__(self, message: str, *, code: str = VARIABLE_NOT_FOUND) -> None:
        self.code = code
        super().__init__(message)


class SecretLeakError(ValueError):
    """试图把 secret 写入持久化数据。"""


__all__ = [
    "FIXTURE_NOT_FOUND",
    "OUTPUT_SCHEMA_MISMATCH",
    "SECRET_UNAVAILABLE",
    "SecretLeakError",
    "VARIABLE_NOT_ANCESTOR",
    "VARIABLE_NOT_FOUND",
    "VariableResolutionError",
]
