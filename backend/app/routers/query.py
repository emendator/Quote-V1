"""智能查询 API"""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.schemas import ApiResponse, SmartQueryRequest, BatchModelQueryRequest
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


@router.post("/batch-models", response_model=ApiResponse)
async def batch_model_query(data: BatchModelQueryRequest, db: AsyncSession = Depends(get_db)):
    """批量快查型号查询：输入多个快查型号（每行一个），返回各自的代发价等信息"""
    # 过滤空字符串
    queries = [q.strip() for q in data.queries if q and q.strip()]
    if not queries:
        return ApiResponse(code=400, message="请输入至少一个快查型号")

    if len(queries) > 500:
        return ApiResponse(code=400, message="批量查询数量不能超过500个")

    result = await query_engine.execute_batch_model_query(db, queries, fuzzy=data.fuzzy)
    return ApiResponse(data=result)
