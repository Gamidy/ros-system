"""图片上传接口"""
import os, uuid
from pathlib import Path
from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
from starlette.responses import JSONResponse
from app.core.database import get_db
from app.core.security import get_current_user
from sqlalchemy.orm import Session
from app.models.user import User

router = APIRouter(prefix="/upload", tags=["upload"])

# 上传目录 - Docker容器内 /app/static/uploads/
UPLOAD_DIR = Path("/app/static/uploads")
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp"}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB

@router.post("/image")
async def upload_image(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """上传竞品外观图片，返回可访问的URL"""
    # 检查文件扩展名
    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail=f"不支持的文件格式: {ext}，支持: {', '.join(ALLOWED_EXTENSIONS)}")

    # 确保目录存在
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

    # 生成唯一文件名
    unique_name = f"{uuid.uuid4().hex}{ext}"
    file_path = UPLOAD_DIR / unique_name

    # 写入文件
    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail=f"文件过大，最大支持 {MAX_FILE_SIZE // 1024 // 1024}MB")

    with open(file_path, "wb") as f:
        f.write(content)

    # 返回URL (nginx代理了/api/到容器)
    url = f"/api/uploads/{unique_name}"
    return JSONResponse({
        "url": url,
        "filename": unique_name,
        "size": len(content),
    })
