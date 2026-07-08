"""AI 供应商配置管理 API — CRUD + 测试连接 + 调用日志"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, Integer
from pydantic import BaseModel
from typing import Optional
from app.core.database import get_db
from app.core.permissions import require_role
from app.core.security import get_current_user
from app.models.ai_config import AIConfig
from app.models.ai_call_log import AICallLog

router = APIRouter(prefix="/admin/ai-configs", tags=["admin-ai-config"])

# ── Pydantic schema ──

class AIConfigCreate(BaseModel):
    provider: str
    model: str
    api_key: str
    api_base: Optional[str] = ""
    temperature: Optional[float] = 0.7
    max_tokens: Optional[int] = 4096

class AIConfigUpdate(BaseModel):
    provider: Optional[str] = None
    model: Optional[str] = None
    api_key: Optional[str] = None
    api_base: Optional[str] = None
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None
    enabled: Optional[bool] = None


# ── CRUD ──

@router.get("")
def list_configs(
    db: Session = Depends(get_db),
    _=Depends(require_role("admin")),
) -> dict:
    """获取所有 AI 供应商配置（API Key 不回显）"""
    rows = db.query(AIConfig).order_by(AIConfig.created_at.desc()).all()
    data = []
    for r in rows:
        data.append({
            "id": r.id,
            "provider": r.provider,
            "model": r.model,
            "api_base": r.api_base or "",
            "api_key": "***",  # 不回显
            "temperature": r.temperature,
            "max_tokens": r.max_tokens,
            "enabled": r.enabled,
            "created_at": r.created_at.isoformat() if r.created_at else None,
            "updated_at": r.updated_at.isoformat() if r.updated_at else None,
        })
    return {"data": data}


@router.post("")
def create_config(
    body: AIConfigCreate,
    db: Session = Depends(get_db),
    _=Depends(require_role("admin")),
) -> dict:
    """创建 AI 供应商配置"""
    config = AIConfig(
        provider=body.provider,
        model=body.model,
        api_base=body.api_base or None,
        temperature=body.temperature if body.temperature is not None else 0.7,
        max_tokens=body.max_tokens if body.max_tokens is not None else 4096,
        enabled=True,
    )
    config.set_api_key(body.api_key)
    db.add(config)
    db.commit()
    db.refresh(config)
    return {
        "data": {
            "id": config.id,
            "provider": config.provider,
            "model": config.model,
        }
    }


@router.put("/{config_id}")
def update_config(
    config_id: int,
    body: AIConfigUpdate,
    db: Session = Depends(get_db),
    _=Depends(require_role("admin")),
) -> dict:
    """更新 AI 供应商配置"""
    config = db.query(AIConfig).filter(AIConfig.id == config_id).first()
    if not config:
        raise HTTPException(404, "配置不存在")

    if body.provider is not None:
        config.provider = body.provider
    if body.model is not None:
        config.model = body.model
    if body.api_key is not None and body.api_key:
        config.set_api_key(body.api_key)
    if body.api_base is not None:
        config.api_base = body.api_base or None
    if body.temperature is not None:
        config.temperature = body.temperature
    if body.max_tokens is not None:
        config.max_tokens = body.max_tokens
    if body.enabled is not None:
        config.enabled = body.enabled

    db.commit()
    return {"ok": True}


@router.delete("/{config_id}")
def delete_config(
    config_id: int,
    db: Session = Depends(get_db),
    _=Depends(require_role("admin")),
) -> dict:
    """删除 AI 供应商配置"""
    config = db.query(AIConfig).filter(AIConfig.id == config_id).first()
    if not config:
        raise HTTPException(404, "配置不存在")
    db.delete(config)
    db.commit()
    return {"ok": True}


@router.post("/{config_id}/test")
def test_connection(
    config_id: int,
    db: Session = Depends(get_db),
    _=Depends(require_role("admin")),
) -> dict:
    """测试 AI 连接 — 发送简单请求验证配置有效性"""
    config = db.query(AIConfig).filter(AIConfig.id == config_id).first()
    if not config:
        raise HTTPException(404, "配置不存在")

    import openai
    import time
    import uuid
    from app.models.ai_call_log import AICallLog
    import logging
    logger = logging.getLogger(__name__)

    client = openai.OpenAI(
        api_key=config.get_api_key(),
        base_url=config.api_base or None,
    )

    request_id = str(uuid.uuid4())
    start = time.time()
    success = True
    error_msg = None
    prompt_tokens = 0
    completion_tokens = 0

    try:
        resp = client.chat.completions.create(
            model=config.model,
            messages=[{"role": "user", "content": "Hello, reply 'OK' only."}],
            max_tokens=10,
            temperature=0,
        )
        elapsed_ms = int((time.time() - start) * 1000)
        prompt_tokens = resp.usage.prompt_tokens if resp.usage else 0
        completion_tokens = resp.usage.completion_tokens if resp.usage else 0
        content = (resp.choices[0].message.content or "").strip()
        logger.info("AI test OK: %s (%dms) reply=%s", config.provider, elapsed_ms, content)
    except Exception as e:
        logger.exception("unexpected error")
        elapsed_ms = int((time.time() - start) * 1000)
        success = False
        error_msg = str(e)
        logger.warning("AI test FAILED: %s — %s", config.provider, error_msg)

    # 记录调用日志
    log = AICallLog(
        request_id=request_id,
        provider=config.provider,
        model=config.model,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        cost=0.0,
        response_time_ms=elapsed_ms,
        success=success,
        error=error_msg,
    )
    db.add(log)
    db.commit()

    if not success:
        raise HTTPException(400, f"连接测试失败: {error_msg}")

    return {
        "data": {
            "success": True,
            "message": f"连接成功！耗时 {elapsed_ms}ms",
            "response_time_ms": elapsed_ms,
        }
    }


# ── 调用日志（独立路由，匹配前端 /admin/ai-call-logs）──

logs_router = APIRouter(prefix="/admin/ai-call-logs", tags=["admin-ai-config"])

@logs_router.get("")
def list_call_logs(
    page: int = 1,
    page_size: int = 200,
    provider: Optional[str] = None,
    db: Session = Depends(get_db),
    _=Depends(require_role("admin")),
) -> dict:
    """获取 AI 调用日志"""
    q = db.query(AICallLog)
    if provider:
        q = q.filter(AICallLog.provider == provider)

    total = q.count()
    q = q.order_by(desc(AICallLog.created_at)).offset((page - 1) * page_size).limit(page_size)
    items = q.all()

    # 统计
    stats = db.query(
        func.coalesce(func.sum(AICallLog.prompt_tokens + AICallLog.completion_tokens), 0).label("total_tokens"),
        func.coalesce(func.sum(AICallLog.cost), 0).label("total_cost"),
        func.coalesce(
            func.sum(AICallLog.success.cast(Integer)) * 1.0 / func.nullif(func.count(AICallLog.id), 0),
            0
        ).label("success_rate"),
    ).first()

    return {
        "data": {
            "items": [
                {
                    "id": r.id,
                    "request_id": r.request_id,
                    "provider": r.provider,
                    "model": r.model,
                    "prompt_tokens": r.prompt_tokens,
                    "completion_tokens": r.completion_tokens,
                    "cost": r.cost,
                    "response_time_ms": r.response_time_ms,
                    "success": r.success,
                    "error": r.error,
                    "created_at": r.created_at.isoformat() if r.created_at else None,
                }
                for r in items
            ],
            "total": total,
            "total_tokens": float(stats.total_tokens) if stats else 0,
            "total_cost": float(stats.total_cost) if stats else 0,
            "success_rate": float(stats.success_rate) if stats and stats.success_rate is not None else 0,
        }
    }
