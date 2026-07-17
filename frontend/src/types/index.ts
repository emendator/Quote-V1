// 商品数据类型
export interface Product {
    id: number;
    quick_model: string;
    product_model: string;
    product_name: string;
    brand: string;
    category_level1: string;
    category_level2: string;
    category_level3: string;
    negotiation_price: number | null;
    price_update: string;
    last_purchase_price: number | null;
    purchase_price: number | null;
    retail_price: number | null;
    discount_rate: number;
    new_event_price: number | null;
    shop_url: string;
    bid_price: number | null;
    group_purchase_price: number | null;
    price: number;
    gross_weight: number | null;
    box_spec: string;
    cooperation_level: string;
    supply_status: string;
    specification: string;
    remark: string;
    shipping_fee: number | null;
    barcode_69: string;
    sales_volume: number;
    recommendation: string;
    parameters: string;
    cert_3c: string;
    image: string;
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
    ai_interpretation?: string;
    parsed_params: Record<string, unknown>;
    parsed_queries: ParsedQuery[];
    results: Product[];
    result_count: number;
    message: string;
    unrecognized_text: string;
}

// ========== 批量快查型号查询 ==========

export interface BatchModelQueryItem {
    query: string;
    results: Product[];
    count: number;
    message: string;
}

export interface BatchModelQueryResult {
    total_queries: number;
    total_results: number;
    items: BatchModelQueryItem[];
}

export interface BatchModelQueryRequest {
    queries: string[];
    fuzzy: boolean;
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

// ========== 平台配置相关 ==========

export interface PlatformConfig {
    id: number;
    name: string;
    platform_type: string;
    api_base_url: string;
    api_key: string;
    api_secret: string;
    shop_id: string;
    extra_config: Record<string, unknown>;
    is_active: boolean;
    created_at: string;
    updated_at: string;
}

export interface PlatformConfigCreate {
    name: string;
    platform_type: string;
    api_base_url?: string;
    api_key?: string;
    api_secret?: string;
    shop_id?: string;
    extra_config?: Record<string, unknown>;
    is_active?: boolean;
}

export interface PlatformConfigUpdate {
    name?: string;
    platform_type?: string;
    api_base_url?: string;
    api_key?: string;
    api_secret?: string;
    shop_id?: string;
    extra_config?: Record<string, unknown>;
    is_active?: boolean;
}

// ========== 一键上架相关 ==========

export interface ListingSubmitRequest {
    product_ids: number[];
    platform_ids: number[];
}

export interface ListingResultItem {
    product_id: number;
    platform_id: number;
    status: string;
    platform_product_id: string;
    error_message: string;
}

export interface ListingSubmitResponse {
    total: number;
    success: number;
    failed: number;
    results: ListingResultItem[];
}

export interface ListingLog {
    id: number;
    product_id: number;
    product_model: string;
    product_name: string;
    platform_id: number;
    platform_name: string;
    status: string;
    platform_product_id: string;
    error_message: string;
    created_at: string;
}

export interface ListingLogDetail extends ListingLog {
    request_data: Record<string, unknown>;
    response_data: Record<string, unknown>;
}

export interface ListingLogQuery {
    page?: number;
    page_size?: number;
    status?: string;
    platform_id?: number;
    product_id?: number;
}

export interface PaginatedListingLogs {
    items: ListingLog[];
    total: number;
    page: number;
    page_size: number;
}

export interface TestConnectionResult {
    success: boolean;
    message: string;
}
