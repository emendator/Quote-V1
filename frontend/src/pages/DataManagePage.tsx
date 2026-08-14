import { useState, useEffect, useCallback } from 'react';
import { Button, Input, Space, message, Select, Slider, Typography, Tooltip, Alert } from 'antd';
import { DownloadOutlined, PlusOutlined, ImportOutlined, ReloadOutlined, ZoomInOutlined, ZoomOutOutlined, ColumnHeightOutlined } from '@ant-design/icons';
import ProductTable from '../components/ProductTable';
import ProductForm from '../components/ProductForm';
import ImportDialog from '../components/ImportDialog';
import ColumnDisplayConfig from '../components/ColumnDisplayConfig';
import {
    fetchProducts, fetchCategories, deleteProduct, batchDeleteProducts, exportProducts, getColumnDisplayConfig,
    fetchFilterOptions,
} from '../services/api';
import type { Product, ColumnConfigItem } from '../types';
import { usePageState } from '../store/PageStateContext';
import { useAuth } from '../store/AuthContext';

const { Search } = Input;
const { Text } = Typography;

export default function DataManagePage() {
    const { isSuperAdmin, isAdmin, isGuest } = useAuth();
    const canWrite = isSuperAdmin || isAdmin || isGuest;  // 是否有增删改权限（含游客体验模式）
    const [products, setProducts] = useState<Product[]>([]);
    const [loading, setLoading] = useState(false);
    const [total, setTotal] = useState(0);
    const [categories, setCategories] = useState<string[]>([]);
    const [selectedKeys, setSelectedKeys] = useState<number[]>([]);

    // 持久化状态：切换页面后保留分页/搜索/缩放/排序
    const [pageState, setPageState] = usePageState('data', {
        page: 1,
        pageSize: 20,
        keyword: '',
        category: undefined as string | undefined,
        zoom: 100,
        sortBy: 'created_at' as string,
        sortOrder: 'desc' as string,
    });
    const { page, pageSize, keyword, category, zoom, sortBy, sortOrder } = pageState;
    const updateState = useCallback((patch: Partial<typeof pageState>) => {
        setPageState({ ...pageState, ...patch });
    }, [pageState, setPageState]);

    // 表单弹窗
    const [formOpen, setFormOpen] = useState(false);
    const [editingProduct, setEditingProduct] = useState<Product | null>(null);

    // 导入弹窗
    const [importOpen, setImportOpen] = useState(false);

    // 列显示配置弹窗
    const [columnConfigOpen, setColumnConfigOpen] = useState(false);

    // 表头下拉筛选状态（类似 Excel 的列筛选）
    const [columnFilters, setColumnFilters] = useState<Record<string, string[]>>({});

    // 表头下拉筛选可选值（全量数据，从 API 加载）
    const [filterOptions, setFilterOptions] = useState<Record<string, string[]> | undefined>(undefined);

    // 产品库列显示配置（从 API 加载）
    const [columnConfig, setColumnConfig] = useState<ColumnConfigItem[] | undefined>(undefined);

    // 表格缩放
    const ZOOM_MIN = 50;
    const ZOOM_MAX = 200;
    const ZOOM_STEP = 10;

    const loadColumnConfig = useCallback(async () => {
        try {
            const data = await getColumnDisplayConfig('product_db');
            setColumnConfig(data.columns || []);
        } catch {
            // 加载列配置失败时使用默认配置
            setColumnConfig(undefined);
        }
    }, []);

    const loadData = useCallback(async () => {
        setLoading(true);
        try {
            // 将 columnFilters 转为 JSON 字符串传给后端
            const filtersStr = Object.keys(columnFilters).length > 0
                ? JSON.stringify(columnFilters) : undefined;
            const [data, , opts] = await Promise.all([
                fetchProducts({
                    page,
                    page_size: pageSize,
                    keyword: keyword || undefined,
                    category,
                    sort_by: sortBy,
                    sort_order: sortOrder,
                    filters: filtersStr,
                }),
                loadColumnConfig(),
                fetchFilterOptions().catch(() => undefined),
            ]);
            setProducts(data.items);
            setTotal(data.total);
            if (opts) setFilterOptions(opts);
        } catch (err: unknown) {
            const msg = err instanceof Error ? err.message : '加载失败';
            message.error(msg);
        } finally {
            setLoading(false);
        }
    }, [page, pageSize, keyword, category, sortBy, sortOrder, loadColumnConfig, columnFilters]);

    const loadCategories = async () => {
        try {
            const cats = await fetchCategories();
            setCategories(cats);
        } catch {
            // ignore
        }
    };

    useEffect(() => {
        loadData();
        loadCategories();
    }, [loadData]);

    const handleSearch = (value: string) => {
        updateState({ keyword: value, page: 1 });
    };

    const handleAdd = () => {
        setEditingProduct(null);
        setFormOpen(true);
    };

    const handleEdit = (record: Product) => {
        setEditingProduct(record);
        setFormOpen(true);
    };

    const handleDelete = async (id: number) => {
        try {
            await deleteProduct(id);
            message.success('删除成功');
            loadData();
        } catch (err: unknown) {
            const msg = err instanceof Error ? err.message : '删除失败';
            message.error(msg);
        }
    };

    const handleBatchDelete = async () => {
        if (selectedKeys.length === 0) return;
        setLoading(true);
        try {
            await batchDeleteProducts(selectedKeys);
            message.success(`成功删除 ${selectedKeys.length} 个商品`);
            setSelectedKeys([]);
            loadData();
        } catch (err: unknown) {
            const msg = err instanceof Error ? err.message : '批量删除失败';
            message.error(msg);
        } finally {
            setLoading(false);
        }
    };

    const handleExport = async () => {
        try {
            await exportProducts({
                keyword: keyword || undefined,
                category,
            });
            message.success('导出成功');
        } catch (err: unknown) {
            const msg = err instanceof Error ? err.message : '导出失败';
            message.error(msg);
        }
    };

    return (
        <div>
            {isGuest && (
                <Alert
                    type="warning"
                    showIcon
                    className="dd-module dd-d1"
                    style={{ marginBottom: 16 }}
                    message="游客模式：导入和新增的商品均为临时数据，退出登录后自动清除"
                />
            )}
            <div className="toolbar dd-module dd-d2">
                <Search
                    placeholder="搜索快查型号/型号/品牌/商品名称/69码"
                    allowClear
                    onSearch={handleSearch}
                    style={{ width: 280 }}
                />
                <Select
                    placeholder="筛选分类"
                    allowClear
                    style={{ width: 150 }}
                    value={category}
                    onChange={(val) => {
                        updateState({ category: val, page: 1 });
                    }}
                    options={categories.map((c) => ({ value: c, label: c }))}
                />
                <div style={{ flex: 1 }} />
                <Space>
                    {/* 缩放控制 */}
                    <Button
                        size="small"
                        icon={<ZoomOutOutlined />}
                        disabled={zoom <= ZOOM_MIN}
                        onClick={() => updateState({ zoom: Math.max(ZOOM_MIN, zoom - ZOOM_STEP) })}
                    />
                    <Slider
                        style={{ width: 80, margin: '0 4px' }}
                        min={ZOOM_MIN}
                        max={ZOOM_MAX}
                        step={ZOOM_STEP}
                        value={zoom}
                        onChange={(v) => updateState({ zoom: v })}
                        tooltip={{ formatter: (v) => `${v}%` }}
                    />
                    <Button
                        size="small"
                        icon={<ZoomInOutlined />}
                        disabled={zoom >= ZOOM_MAX}
                        onClick={() => updateState({ zoom: Math.min(ZOOM_MAX, zoom + ZOOM_STEP) })}
                    />
                    <Text type="secondary" style={{ fontSize: 12, minWidth: 36, textAlign: 'center' }}>
                        {zoom}%
                    </Text>
                    <Button icon={<ReloadOutlined />} onClick={loadData}>
                        刷新
                    </Button>
                    <Button icon={<DownloadOutlined />} onClick={handleExport}>
                        导出数据
                    </Button>
                    <Tooltip title="配置商品表格的列显示和表头名称（管理员以上可配置）">
                        <Button
                            icon={<ColumnHeightOutlined />}
                            onClick={() => setColumnConfigOpen(true)}
                        >
                            列配置
                        </Button>
                    </Tooltip>
                    {canWrite && (
                        <>

                            <Button icon={<ImportOutlined />} onClick={() => setImportOpen(true)}>
                                导入数据
                            </Button>
                            <Button type="primary" icon={<PlusOutlined />} onClick={handleAdd} className="dd-shimmer">
                                新增商品
                            </Button>
                        </>
                    )}
                </Space>
            </div>

            <div className="dd-module dd-d3">
                <ProductTable
                    dataSource={products}
                    loading={loading}
                    total={total}
                    page={page}
                    pageSize={pageSize}
                    selectedRowKeys={selectedKeys}
                    zoom={zoom}
                    sortBy={sortBy}
                    sortOrder={sortOrder}
                    columnFilters={columnFilters}
                    onColumnFilter={(filters) => {
                        setColumnFilters(filters);
                        updateState({ page: 1 });  // 筛选后回到第一页
                    }}
                    canWrite={canWrite}
                    columnConfig={columnConfig}
                    filterOptions={filterOptions}
                    onPageChange={(p, ps) => {
                        updateState({ page: p, pageSize: ps });
                    }}
                    onSortChange={(field, order) => {
                        updateState({ sortBy: field, sortOrder: order, page: 1 });
                    }}
                    onEdit={handleEdit}
                    onDelete={handleDelete}
                    onBatchDelete={handleBatchDelete}
                    onSelectChange={setSelectedKeys}
                />
            </div>

            {canWrite && (
                <>
                    <ProductForm
                        open={formOpen}
                        editingProduct={editingProduct}
                        onClose={() => setFormOpen(false)}
                        onSuccess={loadData}
                    />
                    <ImportDialog
                        open={importOpen}
                        onClose={() => setImportOpen(false)}
                        onSuccess={loadData}
                    />
                </>
            )}

            <ColumnDisplayConfig
                open={columnConfigOpen}
                pageType="product_db"
                title="商品列显示配置"
                onClose={() => setColumnConfigOpen(false)}
                onSaved={() => {
                    loadData();
                    loadColumnConfig();
                }}
            />
        </div>
    );
}
