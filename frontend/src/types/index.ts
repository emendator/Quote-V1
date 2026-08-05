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

// ========== 列显示配置相关 ==========

export interface ColumnConfigItem {
    key: string;
    label: string;
    visible: boolean;
    width: number;
    fixed?: 'left' | 'right' | null;
}

export interface ColumnDisplayConfigData {
    page_type: string;
    columns: ColumnConfigItem[];
}

export interface AvailableColumn {
    key: string;
    default_label: string;
    default_width: number;
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
    tokens_used?: number;
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

// ========== 用户认证相关 ==========

export type UserRole = 'super_admin' | 'admin' | 'user';

export interface User {
    id: number;
    username: string;
    email: string;
    role: UserRole;
    company_id: number | null;
    company_name: string;
    contact_person: string;
    contact_phone: string;
    company_address: string;
    is_active: boolean;
    has_api_key: boolean;
    total_tokens_used: number;
    expires_at: string | null;
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
    contact_person?: string;
    contact_phone?: string;
    company_address?: string;
}

export interface CompanyBindRequest {
    mode: 'join' | 'create';
    company_name: string;
    company_password: string;
    contact_person?: string;
    contact_phone?: string;
    company_address?: string;
}

export interface CompanyPasswordChangeRequest {
    old_password: string;
    new_password: string;
    /** 最高级管理员可指定要修改的公司（留空=自己所在公司）；普通管理员只能改自己所在公司 */
    company_name?: string;
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
    company_name: string;           // 邀请码预设的公司名称
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

// ========== 智能方案相关（v2.0 组合方案）=========

/** 结构化方案输入：一个商品信息块 */
export interface SolutionSlotInput {
    /** 三级品类（必填，用户从三级品类列表选择） */
    category?: string;
    quantity: number;                // 数量
    /** 价格限制方式：gt(大于) / lt(小于) / around(左右) */
    price_op?: 'gt' | 'lt' | 'around' | '';
    /** 价格限制值 */
    price?: number | null;
    /** 折扣率限制方式：gt(大于) / lt(小于) / around(左右) */
    discount_op?: 'gt' | 'lt' | 'around' | '';
    /** 折扣率限制值（百分比） */
    discount?: number | null;
    price_min?: number | null;       // 价格下限（兼容）
    price_max?: number | null;       // 价格上限（兼容）
    /** 是否展开（前端 UI 状态，仅用于折叠展示，不会发送到后端） */
    expanded?: boolean;
}

export interface SolutionAnalyzeRequest {
    requirement?: string;
    use_ai?: boolean;
    max_solutions?: number;
    /** 结构化输入：总价（必填） */
    total_price?: number | null;
    /** 总价限制方式：gt(大于) / lt(小于) / around(左右) */
    total_price_op?: 'gt' | 'lt' | 'around' | '';
    /** 结构化输入：总折扣率限制值（可选） */
    max_discount_rate?: number | null;
    /** 总折扣率限制方式：gt(大于) / lt(小于) / around(左右) */
    max_discount_op?: 'gt' | 'lt' | 'around' | '';
    /** 结构化输入：商品信息块列表 */
    slots?: SolutionSlotInput[];
}

/** 组合方案中的单个商品 */
export interface SolutionSlotItem {
    product_id: number;
    quick_model: string;
    product_model: string;
    product_name: string;
    brand: string;
    category_level1: string;
    category_level2: string;
    specification: string;
    price: number;
    retail_price: number;
    discount_rate: number;
    image?: string;
    quantity: number;
    subtotal: number;
}

/** 一个完整的组合方案 */
export interface SolutionCombination {
    total_price: number;
    total_quantity: number;
    total_discount_rate: number;
    items: SolutionSlotItem[];
}

/** 智能方案一键调整参数（由后端诊断给出，前端据此应用建议） */
export interface SolutionAdjust {
    /** 调整字段：总价 / 总折扣率 / 某商品的价格 / 折扣率 / 品类 / 移除最后一个商品 / AI模式直接覆盖需求文本 */
    field: 'total_price' | 'total_discount' | 'price' | 'discount' | 'category' | 'remove_last_slot' | 'requirement';
    /** 商品槽位索引（商品级调整时有效） */
    slot_index?: number;
    /** 建议值（AI 模式覆盖需求文本时为字符串） */
    value?: number | string | null;
    /** 限制操作符：gt(大于) / lt(小于) / around(左右) */
    op?: 'gt' | 'lt' | 'around' | '';
}

/** 智能方案无方案诊断条目 */
export interface SolutionDiagnosis {
    /** 诊断类型：total_price / total_discount / slot_price / slot_discount / empty_slot / insufficient / general */
    type: string;
    /** 诊断标题（如"第 1 个品类「耳机」价格上限过低"） */
    title: string;
    /** 问题详情 */
    detail: string;
    /** 智能调整建议 */
    suggestion: string;
    /** 一键调整参数（前端据此提供"应用建议"按钮/下拉） */
    adjust?: SolutionAdjust | null;
}

/** 组合方案分析结果 */
export interface SolutionAnalyzeResult {
    parsed_constraints: Record<string, unknown>;
    ai_interpretation: string;
    solutions: SolutionCombination[];
    total_solutions: number;
    message: string;
    /** 无方案时的结构化诊断条目（供前端渲染智能诊断面板） */
    diagnosis?: SolutionDiagnosis[];
    tokens_used?: number;
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
