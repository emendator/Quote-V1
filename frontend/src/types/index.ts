// 商品数据类型
export interface Product {
    id: number;
    brand: string;
    product_image: string;
    category: string;
    product_model: string;
    specification: string;
    jd_price: number | null;
    cost_price: number | null;
    price: number;
    barcode_69: string;
    supplier: string;
    shop_url: string;
    discount_rate: number;
    stock: number;
    remark: string;
    created_at: string;
    updated_at: string;
}

// 分页响应
export interface PaginatedData {
    items: Product[];
    total: number;
    page: number;
    page_size: number;
}

// API 统一响应
export interface ApiResponse<T = unknown> {
    code: number;
    data: T;
    message: string;
}

// 查询参数
export interface ProductQuery {
    page?: number;
    page_size?: number;
    keyword?: string;
    category?: string;
    sort_by?: string;
    sort_order?: string;
    price_min?: number;
    price_max?: number;
}

// 智能查询请求
export interface SmartQueryRequest {
    query_text: string;
}

// 智能查询响应
export interface ParsedQuery {
    type: string;
    value: string;
    results: Product[];
    count: number;
    message: string;
}

export interface SmartQueryResult {
    query_intent: string;
    parsed_params: Record<string, unknown>;
    parsed_queries: ParsedQuery[];
    results: Product[];
    result_count: number;
    message: string;
    unrecognized_text: string;
}

// 导入相关
export interface UploadResult {
    file_id: string;
    file_name: string;
    columns: string[];
    preview_rows: string[][];
    total_rows: number;
    suggested_mapping: Record<string, string>;
}

export interface ImportConfirmRequest {
    file_id: string;
    column_mapping: Record<string, string>;
    duplicate_strategy: string;
}

export interface ImportResult {
    total_rows: number;
    success_rows: number;
    skip_rows: number;
    error_rows: number;
    errors: { row: number; reason: string }[];
}
