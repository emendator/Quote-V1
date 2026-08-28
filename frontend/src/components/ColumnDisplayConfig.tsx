import { useState, useEffect, useCallback, useRef } from 'react';
import { Modal, Table, Switch, Input, InputNumber, Button, Space, message, Tooltip } from 'antd';
import { HolderOutlined } from '@ant-design/icons';
import { getColumnDisplayConfig, updateColumnDisplayConfig, getAvailableColumns } from '../services/api';
import type { ColumnConfigItem, AvailableColumn } from '../types';

interface Props {
    open: boolean;
    pageType: 'product_db' | 'query_result' | 'batch_query' | 'solution_items';
    title?: string;
    onClose: () => void;
    onSaved?: () => void;
}

export default function ColumnDisplayConfig({ open, pageType, title, onClose, onSaved }: Props) {
    const [columns, setColumns] = useState<ColumnConfigItem[]>([]);
    const [availableColumns, setAvailableColumns] = useState<AvailableColumn[]>([]);
    const [loading, setLoading] = useState(false);
    const [saving, setSaving] = useState(false);

    const loadConfig = useCallback(async () => {
        setLoading(true);
        try {
            const [configData, availData] = await Promise.all([
                getColumnDisplayConfig(pageType),
                getAvailableColumns(pageType),
            ]);
            setColumns(configData.columns || []);
            setAvailableColumns(availData.columns || []);
        } catch (err: unknown) {
            const msg = err instanceof Error ? err.message : '加载配置失败';
            message.error(msg);
        } finally {
            setLoading(false);
        }
    }, [pageType]);

    useEffect(() => {
        if (open) {
            loadConfig();
        }
    }, [open, loadConfig]);

    // 切换列的可见性
    const toggleVisibility = (key: string) => {
        setColumns(prev =>
            prev.map(col =>
                col.key === key ? { ...col, visible: !col.visible } : col
            )
        );
    };

    // 更新列标签
    const updateLabel = (key: string, label: string) => {
        setColumns(prev =>
            prev.map(col =>
                col.key === key ? { ...col, label } : col
            )
        );
    };

    // 更新列宽
    const updateWidth = (key: string, width: number) => {
        setColumns(prev =>
            prev.map(col =>
                col.key === key ? { ...col, width } : col
            )
        );
    };

    // ========== 拖拽排序 ==========
    const dragIndex = useRef<number | null>(null);
    const dropIndex = useRef<number | null>(null);

    const handleDragStart = (index: number) => {
        dragIndex.current = index;
        dropIndex.current = index;
    };

    const handleDragOver = (e: React.DragEvent, index: number) => {
        e.preventDefault();
        dropIndex.current = index;
        // 视觉反馈：设置拖拽经过行的样式（通过 data 属性）
        const target = e.currentTarget as HTMLElement;
        target.style.borderTop = index < (dragIndex.current ?? -1) ? '2px solid var(--accent-indigo)' : '';
        target.style.borderBottom = index > (dragIndex.current ?? -1) ? '2px solid var(--accent-indigo)' : '';
    };

    const handleDragLeave = (e: React.DragEvent) => {
        const target = e.currentTarget as HTMLElement;
        target.style.borderTop = '';
        target.style.borderBottom = '';
    };

    const handleDrop = (e: React.DragEvent) => {
        e.preventDefault();
        const from = dragIndex.current;
        const to = dropIndex.current;
        if (from !== null && to !== null && from !== to) {
            setColumns(prev => {
                const next = [...prev];
                const [removed] = next.splice(from, 1);
                next.splice(to, 0, removed);
                return next;
            });
        }
        dragIndex.current = null;
        dropIndex.current = null;
        // 清除所有行的拖拽样式
        document.querySelectorAll('.ant-table-row').forEach(row => {
            (row as HTMLElement).style.borderTop = '';
            (row as HTMLElement).style.borderBottom = '';
        });
    };

    const handleDragEnd = () => {
        dragIndex.current = null;
        dropIndex.current = null;
        document.querySelectorAll('.ant-table-row').forEach(row => {
            (row as HTMLElement).style.borderTop = '';
            (row as HTMLElement).style.borderBottom = '';
        });
    };

    // 恢复默认配置
    const resetToDefault = async () => {
        setLoading(true);
        try {
            const availData = await getAvailableColumns(pageType);
            // 从可用列重建默认配置（全部可见）
            const defaults = availData.columns.map((avail: AvailableColumn) => ({
                key: avail.key,
                label: avail.default_label,
                visible: true,
                width: avail.default_width,
            }));
            setColumns(defaults);
            message.success('已恢复默认配置，点击"保存"生效');
        } catch (err: unknown) {
            const msg = err instanceof Error ? err.message : '恢复默认失败';
            message.error(msg);
        } finally {
            setLoading(false);
        }
    };

    // 保存
    const handleSave = async () => {
        setSaving(true);
        try {
            await updateColumnDisplayConfig(pageType, columns);
            message.success('列显示配置已保存');
            onSaved?.();
            onClose();
        } catch (err: unknown) {
            const msg = err instanceof Error ? err.message : '保存失败';
            message.error(msg);
        } finally {
            setSaving(false);
        }
    };

    // 找到列的默认标签
    const getDefaultLabel = (key: string): string => {
        const found = availableColumns.find(a => a.key === key);
        return found?.default_label || key;
    };

    const dataSource = columns.map((col, idx) => ({
        ...col,
        defaultLabel: getDefaultLabel(col.key),
        index: idx + 1,
    }));

    const configColumns = [
        {
            title: '拖拽',
            key: 'drag',
            width: 50,
            render: () => (
                <span style={{ cursor: 'grab', color: 'var(--ink-400)', fontSize: 16 }}>
                    <HolderOutlined />
                </span>
            ),
        },
        {
            title: '序号',
            dataIndex: 'index',
            key: 'index',
            width: 60,
        },
        {
            title: '字段名',
            dataIndex: 'key',
            key: 'key',
            width: 140,
            render: (v: string) => <code>{v}</code>,
        },
        {
            title: '表头名称',
            dataIndex: 'label',
            key: 'label',
            width: 200,
            render: (v: string, record: ColumnConfigItem & { defaultLabel: string }) => (
                <Tooltip title={`默认: ${record.defaultLabel}`}>
                    <Input
                        size="small"
                        value={v}
                        onChange={e => updateLabel(record.key, e.target.value)}
                        placeholder={record.defaultLabel}
                    />
                </Tooltip>
            ),
        },
        {
            title: '默认名称',
            dataIndex: 'defaultLabel',
            key: 'defaultLabel',
            width: 120,
            render: (v: string) => <span style={{ color: 'var(--ink-400)' }}>{v}</span>,
        },
        {
            title: '显示',
            dataIndex: 'visible',
            key: 'visible',
            width: 70,
            render: (v: boolean, record: ColumnConfigItem) => (
                <Switch
                    size="small"
                    checked={v}
                    onChange={() => toggleVisibility(record.key)}
                />
            ),
        },
        {
            title: '列宽',
            dataIndex: 'width',
            key: 'width',
            width: 120,
            render: (v: number, record: ColumnConfigItem) => (
                <InputNumber
                    size="small"
                    min={30}
                    max={500}
                    value={v}
                    onChange={val => updateWidth(record.key, val ?? 120)}
                    style={{ width: 80 }}
                />
            ),
        },
    ];

    return (
        <Modal
            title={title || `列显示配置 - ${pageType === 'product_db' ? '商品库' : pageType === 'query_result' ? '智能查询结果' : '批量查询结果'}`}
            open={open}
            onCancel={onClose}
            width={900}
            footer={
                <Space>
                    <Button onClick={resetToDefault} loading={loading}>恢复默认</Button>
                    <Button onClick={onClose}>取消</Button>
                    <Button type="primary" onClick={handleSave} loading={saving}>保存配置</Button>
                </Space>
            }
            destroyOnClose
        >
            <Table
                columns={configColumns}
                dataSource={dataSource}
                rowKey="key"
                loading={loading}
                size="small"
                pagination={false}
                scroll={{ y: 500 }}
                onRow={(_, index) => ({
                    draggable: true,
                    onDragStart: () => handleDragStart(index!),
                    onDragOver: (e) => handleDragOver(e, index!),
                    onDragLeave: (e) => handleDragLeave(e),
                    onDrop: (e) => handleDrop(e),
                    onDragEnd: handleDragEnd,
                    style: { cursor: 'default' },
                })}
            />
            <div style={{ marginTop: 8, color: 'var(--ink-400)', fontSize: 12 }}>
                提示：拖动行前的 ≡ 图标可调整列顺序；关闭「显示」开关可隐藏该列；
                修改「表头名称」可自定义列名；「列宽」单位为像素。修改保存后立即生效。
            </div>
        </Modal>
    );
}
