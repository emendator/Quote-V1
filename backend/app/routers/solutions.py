"""智能方案 API"""
from fastapi import APIRouter, Depends
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.schemas import ApiResponse, SolutionAnalyzeRequest, SolutionSaveRequest, SolutionExportRequest
from app.services.solution_service import solution_service
from app.models import User
from app.utils.auth_utils import get_current_user

router = APIRouter(prefix="/api/solution", tags=["智能方案"])


@router.post("/analyze", response_model=ApiResponse)
async def analyze_requirement(
    data: SolutionAnalyzeRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """分析客户需求，返回筛选出的候选商品列表（数据隔离）"""
    if not data.requirement or not data.requirement.strip():
        if not data.filters or all(v is None or v == "" for v in data.filters.values()):
            return ApiResponse(code=400, message="请输入客户需求或选择筛选条件")

    result = await solution_service.analyze(
        requirement=data.requirement.strip(),
        use_ai=data.use_ai,
        filters=data.filters,
        owner_id=current_user.id,
    )
    return ApiResponse(data=result)


@router.post("/save", response_model=ApiResponse)
async def save_solution(
    data: SolutionSaveRequest,
    current_user: User = Depends(get_current_user),
):
    """保存方案到数据库"""
    if not data.items:
        return ApiResponse(code=400, message="方案中至少需要一个商品")

    result = solution_service.save_plan(
        name=data.name,
        requirement=data.requirement,
        ai_enabled=data.ai_enabled,
        items=data.items,
        remark=getattr(data, 'remark', ''),
        owner_id=current_user.id,
    )
    return ApiResponse(data=result)


@router.post("/export")
async def export_solution(
    data: SolutionExportRequest,
    current_user: User = Depends(get_current_user),
):
    """导出方案为 DOCX 文档"""
    try:
        docx_bytes = solution_service.export_docx(plan_id=data.plan_id)
        return Response(
            content=docx_bytes,
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            headers={
                "Content-Disposition": f"attachment; filename=solution_{data.plan_id}.docx",
                "Content-Length": str(len(docx_bytes)),
            },
        )
    except ValueError as e:
        return ApiResponse(code=404, message=str(e))
    except Exception as e:
        return ApiResponse(code=500, message=f"导出失败: {str(e)}")


@router.get("/list", response_model=ApiResponse)
async def list_solutions(
    current_user: User = Depends(get_current_user),
):
    """获取所有历史方案列表"""
    plans = solution_service.list_plans(owner_id=current_user.id)
    return ApiResponse(data=plans)


@router.get("/{plan_id}", response_model=ApiResponse)
async def get_solution(
    plan_id: int,
    current_user: User = Depends(get_current_user),
):
    """获取方案详情（含明细）"""
    try:
        detail = solution_service.get_plan_detail(plan_id)
        return ApiResponse(data=detail)
    except ValueError as e:
        return ApiResponse(code=404, message=str(e))


@router.delete("/{plan_id}", response_model=ApiResponse)
async def delete_solution(
    plan_id: int,
    current_user: User = Depends(get_current_user),
):
    """删除方案"""
    solution_service.delete_plan(plan_id)
    return ApiResponse(message="删除成功")
