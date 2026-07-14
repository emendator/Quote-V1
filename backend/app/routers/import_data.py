"""数据导入 API"""
import os
import shutil
import uuid
import traceback
import logging
from fastapi import APIRouter, UploadFile, File
from app.config import UPLOAD_DIR, ALLOWED_EXTENSIONS
from app.schemas import ApiResponse, UploadResponse, ConfirmImportRequest, ImportResultResponse
from app.services.import_service import handle_upload, execute_import

router = APIRouter(prefix="/api/import", tags=["数据导入"])
logger = logging.getLogger("import_api")


@router.post("/upload", response_model=ApiResponse)
async def upload_file(file: UploadFile = File(...)):
    """上传 Excel/CSV 文件并返回预览数据"""
    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        return ApiResponse(code=400, message=f"不支持的文件格式: {ext}")

    # 保存到临时目录
    file_id = str(uuid.uuid4())
    save_path = UPLOAD_DIR / f"{file_id}{ext}"
    with open(save_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    try:
        result = handle_upload(str(save_path), file.filename or "unknown")
        return ApiResponse(data=result)
    except Exception as e:
        logger.error(f"文件上传解析失败: {traceback.format_exc()}")
        return ApiResponse(code=400, message=f"文件解析失败: {str(e)}")


@router.post("/confirm", response_model=ApiResponse)
async def confirm_import(data: ConfirmImportRequest):
    """确认列映射并执行导入"""
    try:
        result = execute_import(data.file_id, data.column_mapping, data.duplicate_strategy)
        return ApiResponse(data=result, message="导入完成")
    except ValueError as e:
        logger.warning(f"导入参数错误: {e}")
        return ApiResponse(code=400, message=str(e))
    except Exception as e:
        logger.error(f"导入执行失败: {traceback.format_exc()}")
        return ApiResponse(code=500, message=f"导入失败: {str(e)}")
