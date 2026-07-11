"""Pydantic v2 通用响应模型"""

from pydantic import BaseModel
from typing import Generic, TypeVar, List, Optional

T = TypeVar("T")


class MessageResponse(BaseModel):
    message: str


class PaginatedResponse(BaseModel, Generic[T]):
    total: int
    page: int
    size: int
    items: List[T]
