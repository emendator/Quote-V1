"""智能查询 API"""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.schemas import ApiResponse, SmartQueryRequest
from app.services.query_engine import query_engine
from app.services.ai_query_service import ai_query_service

router = APIRouter(prefix="/api/query", tags=["智能查询"])


@router.post("/smart", response_model=ApiResponse)
async def smart_query(data: SmartQueryRequest, db: AsyncSession = Depends(get_db)):
    """智能查询入口：支持自然语言、微信群消息等（正则引擎）"""
    if not data.query_text or not data.query_text.strip():
        return ApiResponse(code=400, message="请输入查询内容")

    result = await query_engine.execute_smart_query(db, data.query_text.strip())
    return ApiResponse(data=result)


@router.post("/ai", response_model=ApiResponse)
async def ai_query(data: SmartQueryRequest, db: AsyncSession = Depends(get_db)):
    """AI 智能查询：使用 DeepSeek 分析自然语言后执行查询"""
    if not data.query_text or not data.query_text.strip():
        return ApiResponse(code=400, message="请输入查询内容")

    result = await ai_query_service.process_query(db, data.query_text.strip())
    return ApiResponse(data=result)
