"""AI API Key 管理"""
from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import require_role
from app.models.system_config import SystemConfig
import base64, logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/admin/ai-key", tags=["AI配置"])

AI_KEY_NAME = "ai_api_key"

@router.get("")
def get_ai_key(db: Session = Depends(get_db), _=Depends(require_role("admin"))):
    """获取 AI API Key 状态（不返回明文）"""
    row = db.query(SystemConfig).filter(SystemConfig.key == AI_KEY_NAME).first()
    if row and row.value:
        return {"configured": True, "key_prefix": row.value[:8] + "..." if len(row.value) > 8 else "***"}
    return {"configured": False, "key_prefix": ""}

@router.put("")
def set_ai_key(key: str = Body(..., embed=True), db: Session = Depends(get_db), _=Depends(require_role("admin"))):
    """设置 AI API Key"""
    row = db.query(SystemConfig).filter(SystemConfig.key == AI_KEY_NAME).first()
    if row:
        row.value = key
    else:
        db.add(SystemConfig(key=AI_KEY_NAME, value=key))
    db.commit()
    logger.info("AI API Key 已更新")
    return {"status": "ok", "configured": True}

@router.delete("")
def delete_ai_key(db: Session = Depends(get_db), _=Depends(require_role("admin"))):
    """删除 AI API Key"""
    db.query(SystemConfig).filter(SystemConfig.key == AI_KEY_NAME).delete()
    db.commit()
    return {"status": "ok", "configured": False}
