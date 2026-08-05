"""智能方案 API"""
from fastapi import APIRouter, Depends
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.schemas import ApiResponse, SolutionAnalyzeRequest, SolutionSaveRequest, SolutionExportRequest, SolutionRecommendedRequest
from app.services.solution_service import solution_service
from app.models import User
from app.utils.auth_utils import get_current_user, require_company

router = APIRouter(prefix="/api/solution", tags=["智能方案"])


@router.post("/analyze", response_model=ApiResponse)
async def analyze_requirement(
    data: SolutionAnalyzeRequest,
    current_user: User = Depends(require_company),
    db: AsyncSession = Depends(get_db),
):
    """分析客户需求，返回筛选出的候选商品列表（数据隔离）

    支持两种输入：
    - 结构化输入：total_price + slots（多块输入）
    - 文本输入：requirement（自然语言）
    """
    if not data.slots and (not data.requirement or not data.requirement.strip()):
        return ApiResponse(code=400, message="请输入客户需求或选择筛选条件")

    # 使用 AI 分析时需要 API Key
    if data.use_ai and not current_user.api_key:
        return ApiResponse(code=403, message="未配置 API Key，无法使用 AI 分析功能。请在个人菜单中配置 API Key。")

    result = await solution_service.analyze(
        requirement=data.requirement.strip(),
        use_ai=data.use_ai,
        company_id=current_user.company_id,
        user_id=current_user.id,  # 用于 AI 调用和推荐产品查询
        max_solutions=data.max_solutions,
        total_price=data.total_price,
        slots=data.slots,
        max_discount_rate=data.max_discount_rate,
        total_price_op=data.total_price_op,
        total_discount_op=data.max_discount_op,
    )
    return ApiResponse(data=result)


@router.post("/save", response_model=ApiResponse)
async def save_solution(
    data: SolutionSaveRequest,
    current_user: User = Depends(require_company),
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
        company_id=current_user.company_id,
        company_name=current_user.company_name,
        owner_id=current_user.id,
    )
    return ApiResponse(data=result)


@router.post("/export")
async def export_solution(
    data: SolutionExportRequest,
    current_user: User = Depends(require_company),
):
    """导出方案为 Excel 表格（v2.0）
    
    表格包含产品库中所有字段，最后一列为"备注"列，文件名为方案名称
    """
    try:
        excel_bytes, filename = solution_service.export_excel(plan_id=data.plan_id, company_id=current_user.company_id)
        # 对文件名进行 URL 编码，支持中文文件名
        from urllib.parse import quote
        safe_filename = quote(filename or "方案.xlsx")
        return Response(
            content=excel_bytes,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={
                "Content-Disposition": f"attachment; filename*=UTF-8''{safe_filename}",
                "Content-Length": str(len(excel_bytes)),
            },
        )
    except ValueError as e:
        return ApiResponse(code=404, message=str(e))
    except Exception as e:
        return ApiResponse(code=500, message=f"导出失败: {str(e)}")


@router.post("/recommended", response_model=ApiResponse)
async def get_recommended_solutions(
    data: SolutionRecommendedRequest,
    current_user: User = Depends(require_company),
):
    """为低权限用户生成高权限公司的推荐方案"""
    if not data.requirement or not data.requirement.strip():
        return ApiResponse(code=400, message="请输入产品组合需求")

    result = solution_service.generate_recommended_solutions(
        requirement=data.requirement.strip(),
        company_id=current_user.company_id,
        role=current_user.role,
        user_id=current_user.id,
        max_solutions=data.max_solutions,
    )
    return ApiResponse(data=result)


@router.get("/list", response_model=ApiResponse)
async def list_solutions(
    current_user: User = Depends(require_company),
):
    """获取所有历史方案列表"""
    plans = solution_service.list_plans(company_id=current_user.company_id)
    return ApiResponse(data=plans)


@router.get("/{plan_id}", response_model=ApiResponse)
async def get_solution(
    plan_id: int,
    current_user: User = Depends(require_company),
):
    """获取方案详情（含明细，数据隔离）"""
    try:
        detail = solution_service.get_plan_detail(plan_id, company_id=current_user.company_id)
        return ApiResponse(data=detail)
    except ValueError as e:
        return ApiResponse(code=404, message=str(e))


@router.delete("/{plan_id}", response_model=ApiResponse)
async def delete_solution(
    plan_id: int,
    current_user: User = Depends(require_company),
):
    """删除方案（数据隔离）"""
    try:
        solution_service.delete_plan(plan_id, company_id=current_user.company_id)
        return ApiResponse(message="删除成功")
    except ValueError as e:
        return ApiResponse(code=404, message=str(e))
