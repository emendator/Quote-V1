import { Table, Button, Space, Popconfirm, Tag, Input, Tooltip, Checkbox, Divider } from 'antd';
import { EditOutlined, DeleteOutlined, SearchOutlined, FilterFilled } from '@ant-design/icons';
import type { ColumnsType, TablePaginationConfig } from 'antd/es/table';
import type { FilterDropdownProps } from 'antd/es/table/interface';
import type { Product } from '../types';
import { useState, useMemo, useCallback, useEffect, useRef } from 'react';
import type { FilterValue, SorterResult } from 'antd/es/table/interface';

interface Props {
    dataSource: Product[];
    loading: boolean;
    total: number;
    page: number;
    pageSize: number;
    selectedRowKeys: number[];
    zoom?: number;
    sortBy?: string;
    sortOrder?: string;
    onPageChange: (page: number, pageSize: number) => void;
    onSortChange?: (sortBy: string, sortOrder: string) => void;
    onEdit: (record: Product) => void;
    onDelete: (id: number) => void;
    onBatchDelete: () => void;
    onSelectChange: (keys: number[]) => void;
    /** 当前活跃的列筛选条件 { dataIndex: selectedValues[] } */
    columnFilters?: Record<string, string[]>;
    /** 列筛选变更回调 */
    onColumnFilter?: (filters: Record<string, string[]>) => void;
    /** 是否有写入权限（增删改），普通用户为 false 时隐藏操作列和批量删除 */
    canWrite?: boolean;
    /** 列显示配置（从 API 加载），用于控制列的可见性和自定义表头名称 */
    columnConfig?: { key: string; label: string; visible: boolean; width?: number }[];
    /** 表头下拉筛选项（全量数据，不限于当前页），{ dataIndex: string[] } */
    filterOptions?: Record<string, string[]>;
}

// ========== 可筛选的文本列定义 ==========
// key: dataIndex, label: 显示名称
const FILTERABLE_COLUMNS: { key: string; label: string }[] = [
    { key: 'quick_model', label: '快查型号' },
    { key: 'product_model', label: '型号' },
    { key: 'product_name', label: '商品名称' },
    { key: 'brand', label: '品牌' },
    { key: 'category_level1', label: '一级品类' },
    { key: 'category_level2', label: '二级品类' },
    { key: 'category_level3', label: '三级品类' },
    { key: 'price_update', label: '报价更新' },
    { key: 'shop_url', label: '链接' },
    { key: 'box_spec', label: '箱规' },
    { key: 'cooperation_level', label: '合作等级' },
    { key: 'supply_status', label: '供货状态' },
    { key: 'specification', label: '规格' },
    { key: 'remark', label: '备注' },
    { key: 'barcode_69', label: '69码' },
    { key: 'recommendation', label: '推荐理由' },
    { key: 'parameters', label: '参数' },
    { key: 'cert_3c', label: '3C' },
];

export default function ProductTable({
    dataSource,
    loading,
    total,
    page,
    pageSize,
    selectedRowKeys,
    zoom = 100,
    sortBy,
    sortOrder,
    onPageChange,
    onSortChange,
    onEdit,
    onDelete,
    onBatchDelete,
    onSelectChange,
    columnFilters = {},
    onColumnFilter,
    canWrite = true,
    columnConfig,
    filterOptions,
}: Props) {
    // 长文本渲染
    const renderEllipsis = (text: string) => {
        if (!text) return '-';
        return (
            <Tooltip title={text} overlayStyle={{ maxWidth: 500 }}>
                <span style={{ whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis', display: 'block' }}>
                    {text}
                </span>
            </Tooltip>
        );
    };

    // ========== 从 dataSource 中提取每列的唯一值（用于筛选下拉框） ==========
    // 如果传入了 filterOptions（全量数据），优先使用；否则回退到当前页数据
    const columnUniqueValues = useMemo(() => {
        if (filterOptions) {
            return filterOptions;
        }
        const map: Record<string, string[]> = {};
        FILTERABLE_COLUMNS.forEach(({ key }) => {
            const values = new Set<string>();
            dataSource.forEach(item => {
                const v = (item as unknown as Record<string, unknown>)[key];
                if (v !== null && v !== undefined && v !== '') {
                    values.add(String(v).trim());
                }
            });
            map[key] = Array.from(values).sort((a, b) => a.localeCompare(b, 'zh-CN'));
        });
        return map;
    }, [dataSource, filterOptions]);

    // ========== 构造 filterDropdown 渲染函数 ==========
    // 使用一个外部 ref 持久化搜索关键词，每次输入时通过更新 selectedKeys 触发重渲染
    const searchKeywords = useRef<Record<string, string>>({});

    const renderFilterDropdown = useCallback(
        (dataIndex: string): (props: FilterDropdownProps) => React.ReactNode => {
            return (props: FilterDropdownProps) => {
                const { setSelectedKeys, selectedKeys, confirm, clearFilters } = props;
                const allOptions = columnUniqueValues[dataIndex] || [];
                const currentSelected = selectedKeys as string[];
                const searchKeyword = searchKeywords.current[dataIndex] || '';
                // 添加空白选项
                const optionsWithBlank = ['', ...allOptions.filter(o => o !== '')];
                // 根据搜索关键词过滤显示的选项
                const filteredOptions = searchKeyword
                    ? optionsWithBlank.filter(o => o.toLowerCase().includes(searchKeyword))
                    : optionsWithBlank;
                return (
                    <div style={{ padding: 8, minWidth: 200 }}>
                        <Input
                            size="small"
                            placeholder="搜索..."
                            prefix={<SearchOutlined />}
                            style={{ marginBottom: 8 }}
                            value={searchKeyword}
                            onChange={e => {
                                searchKeywords.current[dataIndex] = e.target.value;
                                // 触发组件重渲染
                                setSelectedKeys([...currentSelected]);
                            }}
                        />
                        <div style={{ maxHeight: 200, overflow: 'auto' }}>
                            <Checkbox
                                checked={currentSelected.length === optionsWithBlank.length && optionsWithBlank.length > 0}
                                indeterminate={currentSelected.length > 0 && currentSelected.length < optionsWithBlank.length}
                                onChange={e => {
                                    if (e.target.checked) {
                                        setSelectedKeys([...optionsWithBlank]);
                                    } else {
                                        setSelectedKeys([]);
                                    }
                                }}
                                style={{ marginBottom: 4 }}
                            >
                                全选 ({optionsWithBlank.length})
                            </Checkbox>
                            <Divider style={{ margin: '4px 0' }} />
                            {filteredOptions.map(opt => (
                                <div key={opt} style={{ padding: '2px 0' }}>
                                    <Checkbox
                                        checked={currentSelected.includes(opt)}
                                        onChange={e => {
                                            if (e.target.checked) {
                                                setSelectedKeys([...currentSelected, opt]);
                                            } else {
                                                setSelectedKeys(currentSelected.filter(k => k !== opt));
                                            }
                                        }}
                                    >
                                        <Tooltip title={opt === '' ? '(空白)' : opt}>
                                            <span style={{
                                                display: 'inline-block',
                                                maxWidth: 180,
                                                overflow: 'hidden',
                                                textOverflow: 'ellipsis',
                                                whiteSpace: 'nowrap',
                                                verticalAlign: 'middle',
                                            }}>
                                                {opt === '' ? <span style={{ color: 'var(--ink-400)' }}>(空白)</span> : opt}
                                            </span>
                                        </Tooltip>
                                    </Checkbox>
                                </div>
                            ))}
                            {filteredOptions.length === 0 && (
                                <div style={{ color: 'var(--ink-400)', padding: '8px 0', textAlign: 'center' }}>无匹配选项</div>
                            )}
                        </div>
                        <Divider style={{ margin: '6px 0' }} />
                        <Space>
                            <Button
                                type="primary"
                                size="small"
                                onClick={() => {
                                    confirm();
                                    // 通知父组件筛选条件变更
                                    if (onColumnFilter) {
                                        const updated = { ...columnFilters };
                                        if (currentSelected.length === 0 || currentSelected.length === optionsWithBlank.length) {
                                            delete updated[dataIndex];
                                        } else {
                                            updated[dataIndex] = currentSelected;
                                        }
                                        onColumnFilter(updated);
                                    }
                                }}
                            >
                                确定
                            </Button>
                            <Button
                                size="small"
                                onClick={() => {
                                    searchKeywords.current[dataIndex] = '';
                                    clearFilters?.();
                                    if (onColumnFilter) {
                                        const updated = { ...columnFilters };
                                        delete updated[dataIndex];
                                        onColumnFilter(updated);
                                    }
                                }}
                            >
                                重置
                            </Button>
                        </Space>
                    </div>
                );
            };
        },
        [columnUniqueValues, columnFilters, onColumnFilter]
    );

    // ========== 判断列是否有活跃的筛选 ==========
    const isFiltered = (dataIndex: string): boolean => {
        return !!columnFilters[dataIndex] && columnFilters[dataIndex]!.length > 0;
    };

    // ========== 为文本列生成带有 filterDropdown 的列定义 ==========
    const makeFilterableColumn = (col: ColumnsType<Product>[number], dataIndex?: string): ColumnsType<Product>[number] => {
        if (!dataIndex || !FILTERABLE_COLUMNS.find(fc => fc.key === dataIndex)) {
            return col;
        }
        return {
            ...col,
            filterDropdown: renderFilterDropdown(dataIndex),
            filterIcon: (filtered: boolean) => (
                <FilterFilled style={{ color: filtered || isFiltered(dataIndex) ? 'var(--accent-indigo)' : undefined, fontSize: 12 }} />
            ),
            filteredValue: columnFilters[dataIndex] || null,
            onFilter: (value, record) => {
                const val = (record as unknown as Record<string, unknown>)[dataIndex];
                return val !== null && val !== undefined && String(val) === value;
            },
        };
    };

    // 根据列显示配置过滤/调整列定义
    const columns = useMemo(() => {
        const allColumns: ColumnsType<Product> = [
            { title: '序号', key: 'index', width: 56, render: (_, __, index) => <span className="dd-index">{(page - 1) * pageSize + index + 1}</span> },
            makeFilterableColumn({ title: '快查型号', dataIndex: 'quick_model', key: 'quick_model', width: 160, ellipsis: { showTitle: false }, render: (v) => renderEllipsis(v) }, 'quick_model'),
            makeFilterableColumn({ title: '型号', dataIndex: 'product_model', key: 'product_model', width: 130, ellipsis: { showTitle: false }, render: (v) => renderEllipsis(v) }, 'product_model'),
            {
                title: '图片',
                dataIndex: 'image',
                key: 'image',
                width: 65,
                render: (v: string) => {
                    if (!v || v === '') {
                        return <span style={{ color: 'var(--ink-300)', fontSize: 12 }}>无图</span>;
                    }
                    const src = v.startsWith('data:') ? v : `data:image/png;base64,${v}`;
                    return (
                        <Tooltip title={<img src={src} style={{ maxWidth: 300, maxHeight: 300 }} alt="预览" />}>
                            <img src={src} alt="" style={{ width: 50, height: 50, objectFit: 'cover', borderRadius: 4, border: '1px solid var(--ink-100)', cursor: 'pointer' }} />
                        </Tooltip>
                    );
                },
            },
            makeFilterableColumn({ title: '商品名称', dataIndex: 'product_name', key: 'product_name', width: 160, ellipsis: { showTitle: false }, render: (v) => renderEllipsis(v) }, 'product_name'),
            makeFilterableColumn({ title: '品牌', dataIndex: 'brand', key: 'brand', width: 70, render: (v) => v || '-' }, 'brand'),
            makeFilterableColumn({ title: '一级品类', dataIndex: 'category_level1', key: 'category_level1', width: 80, render: (v) => v || '-' }, 'category_level1'),
            makeFilterableColumn({ title: '二级品类', dataIndex: 'category_level2', key: 'category_level2', width: 80, render: (v) => v || '-' }, 'category_level2'),
            makeFilterableColumn({ title: '三级品类', dataIndex: 'category_level3', key: 'category_level3', width: 80, render: (v) => v || '-' }, 'category_level3'),
            { title: '备货商谈价', dataIndex: 'negotiation_price', key: 'negotiation_price', width: 80, sorter: true, render: (v) => (v ? `¥${v.toFixed(2)}` : '-') },
            makeFilterableColumn({ title: '报价更新', dataIndex: 'price_update', key: 'price_update', width: 95, sorter: true, render: (v) => v ? (v.match(/^(\d{4}-\d{2}-\d{2})/)?.[1] || v) : '-' }, 'price_update'),
            { title: '上次进货价', dataIndex: 'last_purchase_price', key: 'last_purchase_price', width: 80, sorter: true, render: (v) => (v ? `¥${v.toFixed(2)}` : '-') },
            { title: '进货价', dataIndex: 'purchase_price', key: 'purchase_price', width: 80, sorter: true, render: (v) => (v ? `¥${v.toFixed(2)}` : '-') },
            { title: '零售价', dataIndex: 'retail_price', key: 'retail_price', width: 80, sorter: true, render: (v) => (v ? `¥${v.toFixed(2)}` : '-') },
            { title: '折扣率', dataIndex: 'discount_rate', key: 'discount_rate', width: 70, sorter: true, render: (v) => (v ? `${v}%` : '-') },
            { title: '新活动价', dataIndex: 'new_event_price', key: 'new_event_price', width: 80, sorter: true, render: (v) => (v ? `¥${v.toFixed(2)}` : '-') },
            makeFilterableColumn({
                title: '链接', dataIndex: 'shop_url', key: 'shop_url', width: 180, render: (v) => {
                    if (!v) return '-';
                    const url = v.startsWith('http://') || v.startsWith('https://') ? v : `https://${v}`;
                    return <a href={url} target="_blank" rel="noopener noreferrer" style={{ wordBreak: 'break-all' }}>{v}</a>;
                }
            }, 'shop_url'),
            { title: '投标价', dataIndex: 'bid_price', key: 'bid_price', width: 80, sorter: true, render: (v) => (v ? `¥${v.toFixed(2)}` : '-') },
            { title: '集采价/项目', dataIndex: 'group_purchase_price', key: 'group_purchase_price', width: 80, sorter: true, render: (v) => (v ? `¥${v.toFixed(2)}` : '-') },
            { title: '代发价', dataIndex: 'price', key: 'price', width: 80, sorter: true, render: (v) => (v !== null && v !== undefined && v !== '' ? <span className="price-highlight">¥{Number(v).toFixed(2)}</span> : '-') },
            { title: '毛重(kg)', dataIndex: 'gross_weight', key: 'gross_weight', width: 70, sorter: true, render: (v) => (v ? v.toFixed(2) : '-') },
            makeFilterableColumn({ title: '箱规', dataIndex: 'box_spec', key: 'box_spec', width: 120, render: (v) => v || '-' }, 'box_spec'),
            makeFilterableColumn({ title: '合作等级', dataIndex: 'cooperation_level', key: 'cooperation_level', width: 70, render: (v) => v || '-' }, 'cooperation_level'),
            makeFilterableColumn({ title: '供货状态', dataIndex: 'supply_status', key: 'supply_status', width: 70, render: (v) => v || '-' }, 'supply_status'),
            makeFilterableColumn({ title: '规格', dataIndex: 'specification', key: 'specification', width: 130, ellipsis: { showTitle: false }, render: (v) => renderEllipsis(v) }, 'specification'),
            makeFilterableColumn({ title: '备注', dataIndex: 'remark', key: 'remark', width: 150, ellipsis: { showTitle: false }, render: (v) => renderEllipsis(v) }, 'remark'),
            { title: '代发运费', dataIndex: 'shipping_fee', key: 'shipping_fee', width: 80, sorter: true, render: (v) => (v ? `¥${v.toFixed(2)}` : '-') },
            makeFilterableColumn({ title: '69码', dataIndex: 'barcode_69', key: 'barcode_69', width: 150, render: (v) => v || '-' }, 'barcode_69'),
            { title: '销量', dataIndex: 'sales_volume', key: 'sales_volume', width: 60, sorter: true },
            makeFilterableColumn({ title: '推荐理由', dataIndex: 'recommendation', key: 'recommendation', width: 150, ellipsis: { showTitle: false }, render: (v) => renderEllipsis(v) }, 'recommendation'),
            makeFilterableColumn({ title: '参数', dataIndex: 'parameters', key: 'parameters', width: 100, ellipsis: { showTitle: false }, render: (v) => renderEllipsis(v) }, 'parameters'),
            makeFilterableColumn({ title: '3C', dataIndex: 'cert_3c', key: 'cert_3c', width: 70, render: (v) => v || '-' }, 'cert_3c'),
            {
                title: '导入时间', dataIndex: 'created_at', key: 'created_at', width: 160, sorter: true,
                render: (v) => v ? new Date(v).toLocaleString('zh-CN') : '-',
                defaultSortOrder: sortBy === 'created_at' ? (sortOrder === 'asc' ? 'ascend' : 'descend') : undefined,
            },
            ...(canWrite ? [{
                title: '操作',
                key: 'action',
                width: 120,
                fixed: 'right' as const,
                render: (_: unknown, record: Product) => (
                    <Space size="small">
                        <Button type="link" size="small" icon={<EditOutlined />} onClick={() => onEdit(record)}>
                            编辑
                        </Button>
                        <Popconfirm title={`删除「${record.quick_model || record.product_name || record.id}」？`} description="删除后无法恢复" onConfirm={() => onDelete(record.id)} okText="删除" cancelText="取消">
                            <Button type="link" size="small" danger icon={<DeleteOutlined />}>
                                删除
                            </Button>
                        </Popconfirm>
                    </Space>
                ),
            }] : []),
        ];

        // 如果提供了 columnConfig，根据配置顺序/可见性/标签/宽度重排列
        if (columnConfig && columnConfig.length > 0) {
            const colMap = new Map(allColumns.map(col => [(col as any).key || (col as any).dataIndex, col]));
            const ordered: ColumnsType<Product> = [];

            for (const cfg of columnConfig) {
                if (cfg.visible === false) continue;  // 隐藏的列跳过
                const col = colMap.get(cfg.key);
                if (!col) continue;  // 配置中的列在 allColumns 里不存在（可能是已移除的列）
                ordered.push({
                    ...col,
                    title: cfg.label || col.title,
                    width: cfg.width || (col as any).width,
                });
                colMap.delete(cfg.key);  // 已处理，移除
            }

            // 把配置中未出现的列（如动态添加的）追加到末尾
            for (const [, col] of colMap) {
                const key = (col as any).key || (col as any).dataIndex;
                if (key === 'action' && !canWrite) continue;  // 无权限时不显示操作列
                ordered.push(col);
            }

            return ordered;
        }
        return allColumns;
    }, [page, pageSize, canWrite, columnConfig, columnFilters, sortBy, sortOrder, renderFilterDropdown]);

    return (
        <div>
            {canWrite && selectedRowKeys.length > 0 && (
                <div className="dd-fade-in" style={{ marginBottom: 12 }}>
                    <Popconfirm
                        title={`删除选中的 ${selectedRowKeys.length} 个商品？`}
                        description="删除后无法恢复"
                        onConfirm={onBatchDelete}
                        okText="删除"
                        cancelText="取消"
                    >
                        <Button danger>删除所选 ({selectedRowKeys.length})</Button>
                    </Popconfirm>
                </div>
            )}
            <div style={{ overflow: 'auto', zoom: `${zoom}%` }}>
                <Table
                    rowKey="id"
                    columns={columns}
                    dataSource={dataSource}
                    loading={loading}
                    rowSelection={{
                        selectedRowKeys,
                        onChange: (keys) => onSelectChange(keys as number[]),
                    }}
                    pagination={{
                        current: page,
                        pageSize,
                        total,
                        showSizeChanger: true,
                        showQuickJumper: true,
                        showTotal: (t) => `共 ${t} 条`,
                        onChange: onPageChange,
                        pageSizeOptions: ['10', '20', '50', '100', '200', '500', '1000'],
                    }}
                    onChange={(_pagination: TablePaginationConfig, filters: Record<string, FilterValue | null>, sorter: SorterResult<Product> | SorterResult<Product>[]) => {
                        if (onSortChange && !Array.isArray(sorter)) {
                            const field = (sorter.field as string) || '';
                            const order = sorter.order === 'ascend' ? 'asc' : sorter.order === 'descend' ? 'desc' : '';
                            if (field !== (sortBy || '') || order !== (sortOrder || '')) {
                                onSortChange(field || 'created_at', order || 'desc');
                            }
                        }
                    }}
                    scroll={{ x: 2400 }}
                    size="middle"
                />
            </div>
        </div>
    );
}
