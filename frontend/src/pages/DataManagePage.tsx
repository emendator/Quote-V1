import { useState, useEffect, useCallback } from 'react';
import { Button, Input, Space, message, Select, Slider, Typography } from 'antd';
import { DownloadOutlined, PlusOutlined, ImportOutlined, ReloadOutlined, ZoomInOutlined, ZoomOutOutlined, ShoppingCartOutlined } from '@ant-design/icons';
import ProductTable from '../components/ProductTable';
import ProductForm from '../components/ProductForm';
import ImportDialog from '../components/ImportDialog';
import ListingDialog from '../components/ListingDialog';
import {
    fetchProducts, fetchCategories, deleteProduct, batchDeleteProducts, exportProducts,
} from '../services/api';
import type { Product } from '../types';
import { usePageState } from '../store/PageStateContext';

const { Search } = Input;
const { Text } = Typography;

export default function DataManagePage() {
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

    // 一键上架弹窗
    const [listingOpen, setListingOpen] = useState(false);

    // 表格缩放
    const ZOOM_MIN = 50;
    const ZOOM_MAX = 200;
    const ZOOM_STEP = 10;

    const loadData = useCallback(async () => {
        setLoading(true);
        try {
            const data = await fetchProducts({
                page,
                page_size: pageSize,
                keyword: keyword || undefined,
                category,
                sort_by: sortBy,
                sort_order: sortOrder,
            });
            setProducts(data.items);
            setTotal(data.total);
        } catch (err: unknown) {
            const msg = err instanceof Error ? err.message : '加载失败';
            message.error(msg);
        } finally {
            setLoading(false);
        }
    }, [page, pageSize, keyword, category]);

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
            <div className="toolbar">
                <Search
                    placeholder="搜索快查型号/型号/品牌/产品名称/69码"
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
                    <Button icon={<ImportOutlined />} onClick={() => setImportOpen(true)}>
                        导入数据
                    </Button>
                    <Button
                        icon={<ShoppingCartOutlined />}
                        onClick={() => setListingOpen(true)}
                        disabled={selectedKeys.length === 0}
                    >
                        一键上架 ({selectedKeys.length})
                    </Button>
                    <Button type="primary" icon={<PlusOutlined />} onClick={handleAdd}>
                        新增商品
                    </Button>
                </Space>
            </div>

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

            <ListingDialog
                open={listingOpen}
                selectedProductIds={selectedKeys}
                onClose={() => setListingOpen(false)}
                onSuccess={loadData}
            />
        </div>
    );
}
