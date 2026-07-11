"""用户管理 API"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.core.security import get_current_user, RoleChecker
from app.crud.user import user_crud
from app.schemas.user import UserCreate, UserRead
from app.schemas.common import PaginatedResponse

router = APIRouter(prefix="/users", tags=["用户管理"])


@router.get("", response_model=PaginatedResponse[UserRead])
async def list_users(
    skip: int = 0,
    limit: int = 20,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(RoleChecker("admin")),
):
    users = await user_crud.get_multi(db, skip=skip, limit=limit)
    total = await user_crud.count(db)
    return PaginatedResponse(total=total, page=skip // limit + 1, size=limit, items=users)


@router.post("", response_model=UserRead, status_code=status.HTTP_201_CREATED)
async def create_user(
    data: UserCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(RoleChecker("admin")),
):
    existing = await user_crud.get_by_username(db, username=data.username)
    if existing:
        raise HTTPException(status_code=409, detail="用户名已存在")
    return await user_crud.create(db, obj_in=data.model_dump())
