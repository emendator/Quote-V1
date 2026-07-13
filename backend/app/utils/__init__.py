"""Excel 解析工具"""
import pandas as pd
from typing import Tuple, List, Any, Optional


def parse_excel(file_path: str) -> Tuple[List[str], pd.DataFrame, int]:
    """
    解析 Excel/CSV 文件
    返回: (列名列表, DataFrame, 总行数)
    """
    if file_path.endswith(".csv"):
        df = pd.read_csv(file_path, dtype=str)
    else:
        df = pd.read_excel(file_path, dtype=str)

    # 清理列名（去除空白）
    df.columns = [str(col).strip() for col in df.columns]

    columns = list(df.columns)
    total_rows = len(df)

    return columns, df, total_rows


def get_preview(df: pd.DataFrame, n: int = 10) -> List[List[Any]]:
    """获取前 N 行预览数据"""
    preview_df = df.head(n)
    # 将 NaN 替换为空字符串
    preview_df = preview_df.fillna("")
    return preview_df.values.tolist()
