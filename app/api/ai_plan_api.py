"""
AI辅助策划 — 策划草案生成 API

端点:
- POST /api/ai/generate-plan-draft — 生成结构化策划草案
"""
import json
import logging
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user
from app.core.permissions import require_menu
from app.core.constants import VALID_PRODUCT_TYPES
from app.models.user import User
from app.services.ai.plan_generator import generate_plan_draft

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ai", tags=["AI辅助策划"])


# ── 请求/响应 Schema ──


class GeneratePlanDraftRequest(BaseModel):
    """策划草案生成请求"""
    market_id: int = Field(..., description="目标市场 ID（target_markets 表主键）")
    product_type: str = Field(..., description="产品类型（split_wall / floor_standing / cassette / duct 等）")
    extra_context: Optional[str] = Field(
        None, description="额外上下文信息（JSON 字符串），供 AI 参考"
    )
    provider: str = Field("siliconflow", description="AI 供应商名称")
    model: str = Field("zai-org/GLM-5.2", description="模型名称")
    api_key: Optional[str] = Field(None, description="API 密钥（不传则从 settings 读取）")
    api_base: Optional[str] = Field(None, description="自定义 API Base URL")

    @field_validator('product_type')
    @classmethod
    def validate_product_type(cls, v):
        if v not in VALID_PRODUCT_TYPES:
            raise ValueError(f"不支持的产品类型: {v}")
        return v


class GeneratePlanDraftResponse(BaseModel):
    """策划草案生成响应"""
    success: bool = True
    data: dict[str, Any]
    message: str = "策划草案生成成功"


# ── API 端点 ──


@router.post(
    "/generate-plan-draft",
    response_model=GeneratePlanDraftResponse,
    summary="生成产品策划草案",
    description="基于目标市场数据、AI 分析生成结构化的产品策划草案",
    dependencies=[Depends(require_menu("product-plans"))],
)
async def api_generate_plan_draft(
    req: GeneratePlanDraftRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> GeneratePlanDraftResponse:
    """根据目标市场和产品类型，调用 AI 生成结构化策划草案"""
    try:
        plan_draft = await generate_plan_draft(
            market_id=req.market_id,
            product_type=req.product_type,
            extra_context=req.extra_context,
            db=db,
            provider=req.provider,
            model=req.model,
            api_key=req.api_key,
            api_base=req.api_base,
        )
        return GeneratePlanDraftResponse(data=plan_draft)
    except ValueError as e:
        logger.warning("Plan draft generation failed (input error): %s", e)
        raise HTTPException(status_code=422, detail=str(e))
    except RuntimeError as e:
        logger.error("Plan draft generation failed (runtime): %s", e)
        raise HTTPException(status_code=502, detail=str(e))
    except Exception as e:
        logger.exception("Unexpected plan draft generation error")
        raise HTTPException(status_code=500, detail=f"策划草案生成异常: {str(e)}")
