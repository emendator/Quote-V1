"""缓存文件与内存缓存清理工具"""
import os
import time
import shutil
import logging
from datetime import datetime, timedelta
from typing import Set
from app.config import UPLOAD_DIR

logger = logging.getLogger("cleanup")

# 内存缓存引用（由 import_service 中的 _upload_cache 赋值）
_upload_cache_ref: dict = {}

# 默认配置
FILE_MAX_AGE_HOURS = 1     # 上传文件保留时间（小时）
CACHE_MAX_AGE_HOURS = 1    # 内存缓存保留时间（小时）
CLEANUP_INTERVAL_HOURS = 1 # 清理间隔（小时）


def set_upload_cache_ref(cache_ref: dict):
    """注入 _upload_cache 引用，用于清理过期条目"""
    global _upload_cache_ref
    _upload_cache_ref = cache_ref


def clean_upload_files(max_age_hours: float = FILE_MAX_AGE_HOURS) -> int:
    """
    清理 uploads 目录中超过指定时长的文件。
    返回删除的文件数。
    """
    if not UPLOAD_DIR.exists():
        return 0

    now = time.time()
    cutoff = now - max_age_hours * 3600
    removed = 0

    for fname in os.listdir(str(UPLOAD_DIR)):
        fpath = UPLOAD_DIR / fname
        if fpath.is_file():
            try:
                # 获取文件最后修改时间
                mtime = fpath.stat().st_mtime
                if mtime < cutoff:
                    fpath.unlink()
                    removed += 1
                    logger.info(f"已删除过期上传文件: {fname}")
            except Exception as e:
                logger.warning(f"删除文件失败 {fname}: {e}")

    return removed


def clean_memory_cache(max_age_hours: float = CACHE_MAX_AGE_HOURS) -> int:
    """
    清理 _upload_cache 中过期的内存缓存条目。
    返回清理的条目数。
    """
    global _upload_cache_ref
    if not _upload_cache_ref:
        return 0

    cutoff = datetime.now() - timedelta(hours=max_age_hours)
    expired_keys: Set[str] = set()

    # 注意：_upload_cache 的值是 dict，不含时间戳。
    # 这里使用简化策略：如果条目太多（超过 100 条），清理一半最旧的。
    # 更精确的方案需要 cache 记录时间戳，但当前业务场景中条目很少。
    keys = list(_upload_cache_ref.keys())
    if len(keys) > 100:
        # 清理较早的一半（近似）
        remove_count = len(keys) // 2
        for k in keys[:remove_count]:
            _upload_cache_ref.pop(k, None)
            expired_keys.add(k)
        logger.info(f"内存缓存条目过多，已清理 {remove_count} 条")

    return len(expired_keys)


def clean_all(max_age_hours: float = FILE_MAX_AGE_HOURS) -> dict:
    """执行所有清理任务，返回统计"""
    files_removed = clean_upload_files(max_age_hours)
    cache_removed = clean_memory_cache(max_age_hours)
    return {
        "files_removed": files_removed,
        "cache_entries_removed": cache_removed,
    }
