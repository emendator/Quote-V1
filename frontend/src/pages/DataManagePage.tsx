import { useState, useEffect, useCallback } from 'react';
import { Button, Input, Space, message, Select } from 'antd';
import { DownloadOutlined, PlusOutlined, ImportOutlined, ReloadOutlined } from '@ant-design/icons';
import ProductTable from '../components/ProductTable';
import ProductForm from '../components/ProductForm';
import ImportDialog from '../components/ImportDialog';
import {
    fetchProducts, fetchCategories, deleteProduct, batchDeleteProducts, exportProducts,
} from '../services/api';
import type { Product } from '../types';

const { Search } = Input;

export default function DataManagePage() {
    const [products, setProducts] = useState<Product[]>([]);
    const [loading, setLoading] = useState(false);
    const [total, setTotal] = useState(0);
    const [page, setPage] = useState(1);
    const [pageSize, setPageSize] = useState(20);
    const [keyword, setKeyword] = useState('');
    const [category, setCategory] = useState<string | undefined>(undefined);
    const [categories, setCategories] = useState<string[]>([]);
    const [selectedKeys, setSelectedKeys] = useState<number[]>([]);

    // 表单弹窗
    const [formOpen, setFormOpen] = useState(false);
    const [editingProduct, setEditingProduct] = useState<Product | null>(null);

    // 导入弹窗
    const [importOpen, setImportOpen] = useState(false);

    const loadData = useCallback(async () => {
        setLoading(true);
        try {
            const data = await fetchProducts({
                page,
                page_size: pageSize,
                keyword: keyword || undefined,
                category,
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
        setKeyword(value);
        setPage(1);
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
        try {
            await batchDeleteProducts(selectedKeys);
            message.success(`成功删除 ${selectedKeys.length} 个商品`);
            setSelectedKeys([]);
            loadData();
        } catch (err: unknown) {
            const msg = err instanceof Error ? err.message : '批量删除失败';
            message.error(msg);
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
                    placeholder="搜索商品型号/品牌/69码"
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
                        setCategory(val);
                        setPage(1);
                    }}
                    options={categories.map((c) => ({ value: c, label: c }))}
                />
                <div style={{ flex: 1 }} />
                <Space>
                    <Button icon={<ReloadOutlined />} onClick={loadData}>
                        刷新
                    </Button>
                    <Button icon={<DownloadOutlined />} onClick={handleExport}>
                        导出数据
                    </Button>
                    <Button icon={<ImportOutlined />} onClick={() => setImportOpen(true)}>
                        导入数据
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
                onPageChange={(p, ps) => {
                    setPage(p);
                    setPageSize(ps);
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
        </div>
    );
}
