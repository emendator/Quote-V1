import axios from 'axios';
import type {
    ApiResponse,
    PaginatedData,
    Product,
    ProductQuery,
    SmartQueryRequest,
    SmartQueryResult,
    UploadResult,
    ImportConfirmRequest,
    ImportResult,
} from '../types';

const api = axios.create({
    baseURL: '/api',
    timeout: 30000,
});

// 响应拦截器
api.interceptors.response.use(
    (res) => res.data,
    (err) => {
        const msg = err.response?.data?.message || err.message || '请求失败';
        return Promise.reject(new Error(msg));
    }
);

// ========== 商品 CRUD ==========

export async function fetchProducts(params: ProductQuery): Promise<PaginatedData> {
    const res = await api.get<unknown, ApiResponse<PaginatedData>>('/products', { params });
    return res.data;
}

export async function fetchProduct(id: number): Promise<Product> {
    const res = await api.get<unknown, ApiResponse<Product>>(`/products/${id}`);
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
    const res = await api.delete<unknown, ApiResponse<{ deleted: number }>>('/products/batch/delete', {
        data: { ids },
    });
    return res.data;
}

export async function fetchCategories(): Promise<string[]> {
    const res = await api.get<unknown, ApiResponse<string[]>>('/products/categories');
    return res.data;
}

// ========== 商品图片 ==========

export async function uploadProductImage(id: number, file: File): Promise<Product> {
    const formData = new FormData();
    formData.append('file', file);
    const res = await api.post<unknown, ApiResponse<Product>>(`/products/${id}/image`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
    });
    return res.data;
}

export async function deleteProductImage(id: number): Promise<void> {
    await api.delete(`/products/${id}/image`);
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

    // 触发文件下载
    const response = await fetch(`/api/products/export${queryStr}`);
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

// ========== 数据导入 ==========

export async function uploadFile(file: File): Promise<UploadResult> {
    const formData = new FormData();
    formData.append('file', file);
    const res = await api.post<unknown, ApiResponse<UploadResult>>('/import/upload', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
    });
    return res.data;
}

export async function confirmImport(data: ImportConfirmRequest): Promise<ImportResult> {
    const res = await api.post<unknown, ApiResponse<ImportResult>>('/import/confirm', data);
    return res.data;
}

// ========== 智能查询 ==========

export async function smartQuery(data: SmartQueryRequest): Promise<SmartQueryResult> {
    const res = await api.post<unknown, ApiResponse<SmartQueryResult>>('/query/smart', data);
    return res.data;
}
