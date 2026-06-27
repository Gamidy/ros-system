"""通用 Schema 类型 — 跨模块共享"""

from typing import Generic, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class PaginatedResult(BaseModel, Generic[T]):
    """通用分页响应包装器"""
    items: list[T]
    total: int
    page: int = 1
    page_size: int = 20
