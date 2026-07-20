"""统一返回体 R[T] —— {code, msg, data}。"""
from __future__ import annotations

from typing import Generic, Optional, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class R(BaseModel, Generic[T]):
    code: int = 0
    msg: str = "ok"
    data: Optional[T] = None

    @classmethod
    def ok(cls, data: Optional[T] = None, msg: str = "ok") -> "R[T]":
        return cls(code=0, msg=msg, data=data)

    @classmethod
    def err(cls, code: int = 1, msg: str = "error", data=None) -> "R":
        return cls(code=code, msg=msg, data=data)


class Page(BaseModel, Generic[T]):
    total: int = 0
    page: int = 1
    page_size: int = 20
    items: list[T] = []
