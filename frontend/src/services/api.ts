import axios from 'axios';
import type {
    ApiResponse,
    PaginatedData,
    Product,
    ProductQuery,
    SmartQueryRequest,
    SmartQueryResult,
    BatchModelQueryRequest,
    BatchModelQueryResult,
    UploadResult,
    ImportConfirmRequest,
    ImportResult,
    SolutionAnalyzeRequest,
    SolutionAnalyzeResult,
    SolutionSaveRequest,
    SolutionSaveResult,
    LoginRequest,
    LoginResponse,
    RegisterRequest,
    User,
    CompanyInfoUpdate,
    CompanyBindRequest,
    CompanyPasswordChangeRequest,
    InviteCode,
    RecommendedProductResponse,
    ColumnConfigItem,
    ColumnDisplayConfigData,
    AvailableColumn,
} from '../types';

const api = axios.create({
    baseURL: '/api',
    timeout: 120000, // 默认超时 120 秒
});

// 请求拦截器：自动附加 Token
api.interceptors.request.use(
    (config) => {
        const token = localStorage.getItem('auth_token');
        if (token) {
            config.headers.Authorization = `Bearer ${token}`;
        }
        return config;
    },
    (error) => Promise.reject(error)
);

// 响应拦截器
api.interceptors.response.use(
    (res) => {
        const body = res.data;
        // 后端返回的业务 code 非 200 时也当作错误处理
        if (body && typeof body === 'object' && body.code !== undefined && body.code !== 200) {
            const msg = body.message || '请求失败';
            // 401 未登录/登录过期，清除本地存储并跳转
            if (body.code === 401) {
                localStorage.removeItem('auth_token');
                localStorage.removeItem('auth_user');
                if (window.location.pathname !== '/login' && window.location.pathname !== '/register') {
                    window.location.href = '/login';
                }
            }
            return Promise.reject(new Error(msg));
        }
        return body;
    },
    (err) => {
        // HTTP 层面错误（如网络断开、500等）
        if (err.response?.status === 401) {
            localStorage.removeItem('auth_token');
            localStorage.removeItem('auth_user');
            if (window.location.pathname !== '/login' && window.location.pathname !== '/register') {
                window.location.href = '/login';
            }
        }
        const msg = err.response?.data?.detail || err.response?.data?.message || err.message || '请求失败';
        return Promise.reject(new Error(msg));
    }
);

// ========== 商品 CRUD ==========

export async function fetchProducts(params: ProductQuery & { filters?: string }): Promise<PaginatedData> {
    const res = await api.get<unknown, ApiResponse<PaginatedData>>('/products', { params });
    return res.data;
}

export async function fetchFilterOptions(): Promise<Record<string, string[]>> {
    const res = await api.get<unknown, ApiResponse<Record<string, string[]>>>('/products/filter-options');
    return res.data;
}

export async function createProduct(data: Partial<Product>): Promise<Product> {
    const res = await api.post<unknown, ApiResponse<Product>>('/products', data);
    return res.data;
}

export async function updateProduct(id: number, data: Partial<Product>): Promise<Product> {
    const res = await api.put<unknown, ApiResponse<Product>>(`/products/${id}`, data);
    return res.data;
}

export async function deleteProduct(id: number): Promise<void> {
    await api.delete(`/products/${id}`);
}

export async function batchDeleteProducts(ids: number[]): Promise<{ deleted: number }> {
    const res = await api.post<unknown, ApiResponse<{ deleted: number }>>('/products/batch/delete', { ids });
    return res.data;
}

export async function fetchCategories(): Promise<string[]> {
    const res = await api.get<unknown, ApiResponse<string[]>>('/products/categories');
    return res.data;
}

export async function fetchBrands(): Promise<string[]> {
    const res = await api.get<unknown, ApiResponse<string[]>>('/products/brands');
    return res.data;
}

export async function fetchCategoryLevel2(): Promise<string[]> {
    const res = await api.get<unknown, ApiResponse<string[]>>('/products/categories/level2');
    return res.data;
}

export async function fetchCategoryLevel3(): Promise<string[]> {
    const res = await api.get<unknown, ApiResponse<string[]>>('/products/categories/level3');
    return res.data;
}

// ========== 数据导出 ==========

export async function exportProducts(
    params: ProductQuery = {}
): Promise<void> {
    // 构建查询参数
    const queryParts: string[] = [];
    if (params.keyword) queryParts.push(`keyword=${encodeURIComponent(params.keyword)}`);
    if (params.category) queryParts.push(`category=${encodeURIComponent(params.category)}`);
    if (params.sort_by) queryParts.push(`sort_by=${params.sort_by}`);
    if (params.sort_order) queryParts.push(`sort_order=${params.sort_order}`);
    if (params.price_min !== undefined) queryParts.push(`price_min=${params.price_min}`);
    if (params.price_max !== undefined) queryParts.push(`price_max=${params.price_max}`);
    const queryStr = queryParts.length > 0 ? `?${queryParts.join('&')}` : '';

    // 触发文件下载（使用 fetch 并附带认证 token）
    const token = localStorage.getItem('auth_token') || '';
    const response = await fetch(`/api/products/export${queryStr}`, {
        headers: token ? { 'Authorization': `Bearer ${token}` } : {},
    });
    if (!response.ok) throw new Error('导出失败');

    const blob = await response.blob();
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `商品数据_${new Date().toLocaleDateString('zh-CN').replace(/\//g, '-')}.xlsx`;
    document.body.appendChild(a);
    a.click();
    window.URL.revokeObjectURL(url);
    document.body.removeChild(a);
}

/**
 * 导出查询结果中的商品（含图片嵌入）
 */
export async function exportQueryResults(productIds: number[]): Promise<void> {
    const token = localStorage.getItem('auth_token') || '';
    const response = await fetch('/api/query/export', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            ...(token ? { 'Authorization': `Bearer ${token}` } : {}),
        },
        body: JSON.stringify({ product_ids: productIds }),
    });
    if (!response.ok) throw new Error('导出失败');

    const blob = await response.blob();
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `查询结果_${new Date().toLocaleDateString('zh-CN').replace(/\//g, '-')}.xlsx`;
    document.body.appendChild(a);
    a.click();
    window.URL.revokeObjectURL(url);
    document.body.removeChild(a);
}

// ========== 数据导入 ==========

export async function uploadFile(file: File): Promise<UploadResult> {
    const formData = new FormData();
    formData.append('file', file);
    const res = await api.post<unknown, ApiResponse<UploadResult>>('/import/upload', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
        timeout: 300000, // 上传文件延长到 5 分钟
    });
    return res.data;
}

export async function confirmImport(data: ImportConfirmRequest): Promise<ImportResult> {
    const res = await api.post<unknown, ApiResponse<ImportResult>>('/import/confirm', data);
    if (!res.data) {
        throw new Error(res.message || '导入失败');
    }
    return res.data;
}

// ========== 智能查询 ==========

export async function smartQuery(data: SmartQueryRequest): Promise<SmartQueryResult> {
    const res = await api.post<unknown, ApiResponse<SmartQueryResult>>('/query/smart', data);
    return res.data;
}

export async function aiSmartQuery(data: SmartQueryRequest): Promise<SmartQueryResult> {
    const res = await api.post<unknown, ApiResponse<SmartQueryResult>>('/query/ai', data);
    return res.data;
}

// ========== 批量快查型号查询 ==========

export async function batchModelQuery(data: BatchModelQueryRequest): Promise<BatchModelQueryResult> {
    const res = await api.post<unknown, ApiResponse<BatchModelQueryResult>>('/query/batch-models', data);
    return res.data;
}

// ========== 智能方案 ==========

export async function analyzeSolution(data: SolutionAnalyzeRequest): Promise<SolutionAnalyzeResult> {
    const res = await api.post<unknown, ApiResponse<SolutionAnalyzeResult>>('/solution/analyze', data);
    return res.data;
}

export async function saveSolution(data: SolutionSaveRequest): Promise<SolutionSaveResult> {
    const res = await api.post<unknown, ApiResponse<SolutionSaveResult>>('/solution/save', data);
    return res.data;
}

export async function listSolutions(): Promise<{ id: number; name: string; requirement: string; total_amount: number; status: string; created_at: string }[]> {
    const res = await api.get<unknown, ApiResponse<{ id: number; name: string; requirement: string; total_amount: number; status: string; created_at: string }[]>>('/solution/list');
    return res.data;
}

export async function getSolutionDetail(planId: number): Promise<Record<string, unknown>> {
    const res = await api.get<unknown, ApiResponse<Record<string, unknown>>>(`/solution/${planId}`);
    return res.data;
}

export async function deleteSolution(planId: number): Promise<void> {
    await api.delete(`/solution/${planId}`);
}

export async function getRecommendedSolutions(data: { requirement: string; max_solutions?: number }): Promise<{ solutions: any[]; total_solutions: number; message: string }> {
    const res = await api.post<unknown, ApiResponse<{ solutions: any[]; total_solutions: number; message: string }>>('/solution/recommended', data);
    return res.data;
}

export async function exportSolution(planId: number): Promise<void> {
    const token = localStorage.getItem('auth_token');
    const response = await fetch(`/api/solution/export`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            ...(token ? { 'Authorization': `Bearer ${token}` } : {}),
        },
        body: JSON.stringify({ plan_id: planId }),
    });
    if (!response.ok) throw new Error('导出失败');
    const contentType = response.headers.get('content-type') || '';
    if (contentType.includes('application/json')) {
        const errBody = await response.json();
        throw new Error(errBody?.message || '导出失败');
    }
    // 从 Content-Disposition 中提取文件名
    const disposition = response.headers.get('content-disposition') || '';
    let filename = `方案_${planId}.xlsx`;
    const match = disposition.match(/filename\*?=(?:UTF-8'')?["']?(.+?)["']?(?:;|$)/i);
    if (match) {
        filename = decodeURIComponent(match[1]);
    }
    const blob = await response.blob();
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    window.URL.revokeObjectURL(url);
    document.body.removeChild(a);
}

// ========== 用户认证 ==========

export async function login(data: LoginRequest): Promise<LoginResponse> {
    const res = await api.post<unknown, ApiResponse<LoginResponse>>('/auth/login', data);
    return res.data;
}

/** 游客登录：创建独立临时账号+公司，退出后自动清除全部数据 */
export async function guestLogin(): Promise<LoginResponse> {
    const res = await api.post<unknown, ApiResponse<LoginResponse>>('/auth/guest');
    return res.data;
}

/** 清除当前游客会话的全部使用痕迹（仅游客可调用） */
export async function guestCleanup(): Promise<void> {
    await api.post('/auth/guest/cleanup');
}

export async function register(data: RegisterRequest): Promise<LoginResponse> {
    const res = await api.post<unknown, ApiResponse<LoginResponse>>('/auth/register', data);
    return res.data;
}

export async function getCurrentUser(): Promise<User> {
    const res = await api.get<unknown, ApiResponse<User>>('/auth/me');
    return res.data;
}

export async function updateCompanyInfo(data: CompanyInfoUpdate): Promise<User> {
    const res = await api.put<unknown, ApiResponse<User>>('/auth/me/company', data);
    return res.data;
}

export async function bindCompany(data: CompanyBindRequest): Promise<User> {
    const res = await api.post<unknown, ApiResponse<User>>('/company/bind', data);
    return res.data;
}

export async function changeCompanyPassword(data: CompanyPasswordChangeRequest): Promise<void> {
    await api.put('/company/password', data);
}

export async function changePassword(data: { old_password: string; new_password: string }): Promise<void> {
    await api.put('/auth/me/password', data);
}

export async function updateApiKey(apiKey: string): Promise<void> {
    await api.put('/auth/me/apikey', { api_key: apiKey });
}

// ========== 邀请码管理 ==========

export async function createInviteCode(data: { code_type: string; expires_at: string; company_name: string }): Promise<InviteCode> {
    const res = await api.post<unknown, ApiResponse<InviteCode>>('/invites/create', data);
    return res.data;
}

export async function getInviteCodes(params?: { page?: number; page_size?: number; type?: string; status?: string }): Promise<{ items: InviteCode[]; total: number; page: number; page_size: number }> {
    const res = await api.get<unknown, ApiResponse<{ items: InviteCode[]; total: number; page: number; page_size: number }>>('/invites/list', { params });
    return res.data;
}

export async function deleteInviteCode(id: number): Promise<void> {
    await api.delete(`/invites/${id}`);
}

export async function renewInviteCode(id: number, expires_at: string): Promise<void> {
    await api.post(`/invites/${id}/renew`, { expires_at });
}

export async function verifyInviteCode(code: string): Promise<{ valid: boolean; type: string | null; message: string; company_name?: string }> {
    const res = await api.get<unknown, ApiResponse<{ valid: boolean; type: string | null; message: string; company_name?: string }>>(`/invites/verify/${code}`);
    return res.data;
}

// ========== 推荐产品 ==========

export async function getRecommendedProducts(data: { filters?: Record<string, unknown>; page?: number; page_size?: number }): Promise<RecommendedProductResponse> {
    const res = await api.post<unknown, ApiResponse<RecommendedProductResponse>>('/products/recommended', data);
    return res.data;
}

// ========== 列显示配置 ==========

export async function getColumnDisplayConfig(pageType: string): Promise<ColumnDisplayConfigData> {
    const res = await api.get<unknown, ApiResponse<ColumnDisplayConfigData>>(`/column-display/${pageType}`);
    return res.data;
}

export async function updateColumnDisplayConfig(pageType: string, columns: ColumnConfigItem[]): Promise<ColumnDisplayConfigData> {
    const res = await api.put<unknown, ApiResponse<ColumnDisplayConfigData>>(`/column-display/${pageType}`, { columns });
    return res.data;
}

export async function getAvailableColumns(pageType: string): Promise<{ page_type: string; columns: AvailableColumn[] }> {
    const res = await api.get<unknown, ApiResponse<{ page_type: string; columns: AvailableColumn[] }>>(`/column-display/available-columns/${pageType}`);
    return res.data;
}
