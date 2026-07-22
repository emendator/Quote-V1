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

// ========== 用户认证相关 ==========

export type UserRole = 'super_admin' | 'admin' | 'user';

export interface User {
    id: number;
    username: string;
    email: string;
    role: UserRole;
    company_name: string;
    contact_person: string;
    contact_phone: string;
    company_address: string;
    is_active: boolean;
    created_at: string;
    updated_at: string;
}

export interface LoginRequest {
    username: string;
    password: string;
}

export interface LoginResponse {
    access_token: string;
    token_type: string;
    user: User;
}

export interface RegisterRequest {
    username: string;
    password: string;
    email: string;
    invite_code: string;
}

export interface CompanyInfoUpdate {
    company_name: string;
    contact_person?: string;
    contact_phone?: string;
    company_address?: string;
}

// ========== 邀请码相关 ==========

export interface InviteCode {
    id: number;
    code: string;
    type: 'admin' | 'user';
    created_by: number;
    used_by: number | null;
    used_by_username: string;       // 使用者的用户名
    used_by_company: string;        // 使用者公司名称
    used_by_last_login: string | null;  // 使用者最后登录时间
    used_at: string | null;
    expires_at: string;
    is_used: boolean;
    created_at: string;
}

// ========== 推荐产品相关 ==========

export interface RecommendedProduct {
    id: number;
    quick_model: string;
    product_model: string;
    product_name: string;
    brand: string;
    category_level1: string;
    category_level2: string;
    category_level3: string;
    price: number;
    specification: string;
    supply_status: string;
    image: string;
    source_company_name: string;  // 来源公司名称
    source_role: string;          // 来源角色
}

export interface RecommendedProductResponse {
    items: RecommendedProduct[];
    total: number;
    page: number;
    page_size: number;
    recommendation_note: string;
}

// ========== 智能方案相关 ==========

export interface SolutionAnalyzeRequest {
    requirement: string;
    use_ai: boolean;
    filters?: Record<string, unknown>;
}

export interface SolutionCandidate {
    id: number;
    quick_model: string;
    product_model: string;
    product_name: string;
    brand: string;
    category_level1: string;
    category_level2: string;
    specification: string;
    price: number;
    supply_status: string;
    is_recommended?: boolean;
    source_company_name?: string;
    source_role?: string;
}

export interface SolutionAnalyzeResult {
    parsed_intent: Record<string, unknown>;
    ai_interpretation: string;
    candidates: SolutionCandidate[];
    total_candidates: number;
    message: string;
}

export interface SolutionItemData {
    product_id: number;
    quantity: number;
}

export interface SolutionSaveRequest {
    name: string;
    requirement: string;
    remark?: string;
    ai_enabled: boolean;
    items: SolutionItemData[];
}

export interface SolutionSaveResult {
    plan_id: number;
    name: string;
    total_amount: number;
    items_count: number;
}
