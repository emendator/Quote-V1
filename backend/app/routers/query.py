"""智能查询 API"""
from fastapi import APIRouter, Depends
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.schemas import ApiResponse, SmartQueryRequest, BatchModelQueryRequest, QueryExportRequest
from app.services.query_engine import query_engine
from app.services.ai_query_service import ai_query_service
from app.services import product_service
from app.models import User
from app.utils.auth_utils import require_company

router = APIRouter(prefix="/api/query", tags=["智能查询"])


@router.post("/smart", response_model=ApiResponse)
async def smart_query(
    data: SmartQueryRequest,
    current_user: User = Depends(require_company),
    db: AsyncSession = Depends(get_db),
):
    """智能查询入口：支持自然语言、微信群消息等（正则引擎，数据隔离）"""
    if not data.query_text or not data.query_text.strip():
        return ApiResponse(code=400, message="请输入查询内容")

    result = await query_engine.execute_smart_query(db, data.query_text.strip(), company_id=current_user.company_id)
    return ApiResponse(data=result)


@router.post("/ai", response_model=ApiResponse)
async def ai_query(
    data: SmartQueryRequest,
    current_user: User = Depends(require_company),
    db: AsyncSession = Depends(get_db),
):
    """AI 智能查询：使用 DeepSeek 分析自然语言后执行查询（数据隔离）"""
    if not data.query_text or not data.query_text.strip():
        return ApiResponse(code=400, message="请输入查询内容")

    # 检查是否配置了 API Key
    if not current_user.api_key:
        return ApiResponse(code=403, message="未配置 API Key，无法使用 AI 查询功能。请在个人菜单中配置 API Key。")

    result = await ai_query_service.process_query(db, data.query_text.strip(), company_id=current_user.company_id, user_id=current_user.id)
    return ApiResponse(data=result)


@router.post("/batch-models", response_model=ApiResponse)
async def batch_model_query(
    data: BatchModelQueryRequest,
    current_user: User = Depends(require_company),
    db: AsyncSession = Depends(get_db),
):
    """批量快查型号查询：输入多个快查型号（每行一个），返回各自的代发价等信息（数据隔离）"""
    # 过滤空字符串
    queries = [q.strip() for q in data.queries if q and q.strip()]
    if not queries:
        return ApiResponse(code=400, message="请输入至少一个快查型号")

    if len(queries) > 500:
        return ApiResponse(code=400, message="批量查询数量不能超过500个")

    result = await query_engine.execute_batch_model_query(db, queries, fuzzy=data.fuzzy, company_id=current_user.company_id)
    return ApiResponse(data=result)


@router.post("/export")
async def export_query_results(
    data: QueryExportRequest,
    current_user: User = Depends(require_company),
    db: AsyncSession = Depends(get_db),
):
    """导出查询结果中的商品为 Excel（含图片嵌入）"""
    if not data.product_ids:
        return ApiResponse(code=400, message="请提供要导出的商品 ID 列表")

    excel_bytes = await product_service.export_products_by_ids(
        db, data.product_ids, company_id=current_user.company_id
    )

    from urllib.parse import quote
    return Response(
        content=excel_bytes,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": f"attachment; filename*=UTF-8''{quote('查询结果.xlsx')}",
            "Content-Length": str(len(excel_bytes)),
        },
    )
