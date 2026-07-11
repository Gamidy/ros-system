"""认证 API — POST /api/v1/auth/token"""

from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy import select

from app.database import get_db
from app.core.security import create_access_token, get_current_user
from app.crud.user import user_crud
from app.models.user import Role
from app.schemas.user import LoginRequest, UserCreate, UserRead, Token

router = APIRouter(prefix="/auth", tags=["认证"])
login_limiter = Limiter(key_func=get_remote_address)


@router.post("/token", response_model=Token)
@login_limiter.limit("200/minute")
async def login(request: Request, data: LoginRequest, db: AsyncSession = Depends(get_db)):
    user = await user_crud.authenticate(db, username=data.username, password=data.password)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="用户名或密码错误")
    token = create_access_token(data={"sub": str(user.id), "username": user.username})
    return Token(access_token=token)


@router.post("/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
async def register(data: UserCreate, db: AsyncSession = Depends(get_db)):
    existing = await user_crud.get_by_username(db, username=data.username)
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="用户名已存在")
    return await user_crud.create(db, obj_in=data.model_dump())


@router.get("/me", response_model=UserRead)
async def get_me(user=Depends(get_current_user)):
    return user
