import { useState, useRef } from 'react';
import {
    Modal, Steps, Upload, Button, Table, Radio,
    Result, Space, message, Alert, List, Typography, Tooltip,
} from 'antd';
import {
    InboxOutlined, CheckCircleOutlined, CloseCircleOutlined,
    FileOutlined, RightCircleOutlined,
} from '@ant-design/icons';
import type { RcFile } from 'antd/es/upload';
import ColumnMapping from './ColumnMapping';
import { uploadFile, confirmImport } from '../services/api';
import type { UploadResult, ImportResult } from '../types';

const { Dragger } = Upload;
const { Text } = Typography;

interface UploadItem {
    file: RcFile;
    result: UploadResult;
    mapping: Record<string, string>;
}

interface Props {
    open: boolean;
    onClose: () => void;
    onSuccess: () => void;
}

export default function ImportDialog({ open, onClose, onSuccess }: Props) {
    const [currentStep, setCurrentStep] = useState(0);
    const [uploadItems, setUploadItems] = useState<UploadItem[]>([]);
    const [activeFileId, setActiveFileId] = useState<string | null>(null);
    const [strategy, setStrategy] = useState('skip');
    const [importResult, setImportResult] = useState<ImportResult | null>(null);
    const [loading, setLoading] = useState(false);
    const [uploading, setUploading] = useState(false);
    const processingRef = useRef(false);

    const resetState = () => {
        setCurrentStep(0);
        setUploadItems([]);
        setActiveFileId(null);
        setStrategy('skip');
        setImportResult(null);
    };

    const handleClose = () => {
        resetState();
        onClose();
    };

    const handleFiles = async (files: RcFile[]) => {
        if (processingRef.current) return; // 防止重复触发
        processingRef.current = true;
        setUploading(true);
        const newItems: UploadItem[] = [];
        let hasError = false;

        // 过滤掉已经上传过的文件
        const existingNames = new Set(uploadItems.map((item) => item.file.name));
        const newFiles = files.filter((f) => !existingNames.has(f.name));

        if (newFiles.length === 0) {
            message.info('这些文件已经上传过了');
            processingRef.current = false;
            setUploading(false);
            return;
        }

        for (const file of newFiles) {
            try {
                const result = await uploadFile(file);
                newItems.push({ file, result, mapping: result.suggested_mapping });
            } catch (err: unknown) {
                const msg = err instanceof Error ? err.message : '上传失败';
                message.error(`${file.name} 上传失败: ${msg}`);
                hasError = true;
            }
        }

        if (newItems.length > 0) {
            setUploadItems((prev) => [...prev, ...newItems]);
            if (!activeFileId) {
                setActiveFileId(newItems[0].result.file_id);
            }
            message.success(`成功上传 ${newItems.length} 个文件`);
            setCurrentStep(1);
        }

        if (newItems.length === 0 && hasError) {
            message.error('所有文件上传失败，请重试');
        }

        setUploading(false);
        processingRef.current = false;
    };

    const activeItem = uploadItems.find((item) => item.result.file_id === activeFileId);
    const activeResult = activeItem?.result ?? null;
    const activeMapping = activeItem?.mapping ?? {};

    const updateMapping = (newMapping: Record<string, string>) => {
        setUploadItems((prev) =>
            prev.map((item) =>
                item.result.file_id === activeFileId
                    ? { ...item, mapping: newMapping }
                    : item
            )
        );
    };

    const handleConfirmImport = async () => {
        if (!activeItem) return;

        const mappedFields = Object.values(activeItem.mapping);
        if (!mappedFields.includes('quick_model')) {
            message.warning('请至少映射「快查型号」字段（用于数据去重）');
            return;
        }
        // 型号已改为非必填（仅快查型号和代发价为必填）
        // if (!mappedFields.includes('product_model')) {
        //     message.warning('请至少映射「型号」字段');
        //     return;
        // }

        setLoading(true);
        try {
            const result = await confirmImport({
                file_id: activeItem.result.file_id,
                column_mapping: activeItem.mapping,
                duplicate_strategy: strategy,
            });
            if (!result) {
                message.error('导入失败，未获取到结果');
                return;
            }
            setImportResult(result);
            setCurrentStep(2);
            if (result.error_rows === 0) {
                message.success(`成功导入 ${result.success_rows} 条数据`);
                onSuccess();
            }
        } catch (err: unknown) {
            const msg = err instanceof Error ? err.message : '导入失败';
            message.error(msg);
        } finally {
            setLoading(false);
        }
    };

    const steps = [
        { title: '上传文件' },
        { title: '配置映射' },
        { title: '导入结果' },
    ];

    return (
        <Modal
            title="导入商品数据"
            open={open}
            onCancel={handleClose}
            width={900}
            footer={null}
            destroyOnClose
        >
            <Steps current={currentStep} items={steps} className="import-steps" />

            {/* 步骤 1：上传文件 */}
            {currentStep === 0 && (
                <div>
                    <Dragger
                        accept=".xlsx,.xls,.csv"
                        multiple
                        beforeUpload={(f, fileList) => {
                            handleFiles(fileList as RcFile[]);
                            return false;
                        }}
                        showUploadList={false}
                        disabled={uploading}
                    >
                        <p className="ant-upload-drag-icon">
                            <InboxOutlined />
                        </p>
                        <p className="ant-upload-text">点击或拖拽文件到此区域上传</p>
                        <p className="ant-upload-hint">
                            支持 .xlsx / .xls / .csv 格式，可一次选择多个文件
                        </p>
                    </Dragger>
                    {uploading && (
                        <div style={{ textAlign: 'center', marginTop: 16 }}>
                            <Text type="secondary">正在上传文件，请稍候...</Text>
                        </div>
                    )}
                </div>
            )}

            {/* 步骤 2：配置列映射 */}
            {currentStep === 1 && uploadItems.length > 0 && (
                <div>
                    {/* 文件列表 */}
                    <List
                        size="small"
                        header={<Text strong>已上传文件（点击切换）</Text>}
                        style={{ marginBottom: 16 }}
                        dataSource={uploadItems}
                        renderItem={(item) => {
                            const isActive = item.result.file_id === activeFileId;
                            const fname = item.file.name;
                            const total = item.result.total_rows;
                            return (
                                <List.Item
                                    onClick={() => setActiveFileId(item.result.file_id)}
                                    style={{
                                        cursor: 'pointer',
                                        background: isActive ? '#e6f4ff' : undefined,
                                        borderRadius: 4,
                                        padding: '6px 12px',
                                    }}
                                    extra={
                                        isActive ? <RightCircleOutlined style={{ color: '#1677ff' }} /> : null
                                    }
                                >
                                    <List.Item.Meta
                                        avatar={<FileOutlined />}
                                        title={
                                            <Text strong={isActive} style={{ color: isActive ? '#1677ff' : undefined }}>
                                                {fname}
                                            </Text>
                                        }
                                        description={`共 ${total} 行数据`}
                                    />
                                </List.Item>
                            );
                        }}
                    />

                    {activeResult && (
                        <>
                            <Alert
                                message={`当前文件：${activeItem?.file.name} | 共 ${activeResult.total_rows} 行数据`}
                                type="info"
                                style={{ marginBottom: 12 }}
                                showIcon
                            />
                            <ColumnMapping
                                columns={activeResult.columns}
                                mapping={activeMapping}
                                onChange={updateMapping}
                            />

                            {activeResult.preview_rows.length > 0 && (
                                <div style={{ marginTop: 12 }}>
                                    <h4>数据预览（前 {activeResult.preview_rows.length} 行）</h4>
                                    <Table
                                        columns={activeResult.columns.map((col) => ({
                                            title: col,
                                            dataIndex: col,
                                            key: col,
                                            ellipsis: true,
                                            render: (v: string) => v ? <Tooltip title={v}><span style={{ whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis', display: 'block' }}>{v}</span></Tooltip> : '-',
                                        }))}
                                        dataSource={activeResult.preview_rows.map((row, idx) => {
                                            const obj: Record<string, string> = { key: String(idx) };
                                            activeResult!.columns.forEach((col, i) => {
                                                obj[col] = row[i] ?? '';
                                            });
                                            return obj;
                                        })}
                                        pagination={false}
                                        size="small"
                                        scroll={{ x: 800 }}
                                    />
                                </div>
                            )}

                            <div style={{ marginTop: 16 }}>
                                <span style={{ marginRight: 16 }}>重复数据处理策略（以快查型号为准）：</span>
                                <Radio.Group value={strategy} onChange={(e) => setStrategy(e.target.value)}>
                                    <Radio.Button value="skip">跳过已有</Radio.Button>
                                    <Radio.Button value="overwrite">覆盖更新</Radio.Button>
                                    <Radio.Button value="error">报错提示</Radio.Button>
                                </Radio.Group>
                            </div>

                            <div style={{ marginTop: 24, textAlign: 'right' }}>
                                <Space>
                                    <Button onClick={() => setCurrentStep(0)}>返回上一步</Button>
                                    <Button type="primary" onClick={handleConfirmImport} loading={loading}>
                                        确认导入 ({activeItem?.file.name})
                                    </Button>
                                </Space>
                            </div>
                        </>
                    )}
                </div>
            )}

            {/* 步骤 3：导入结果 */}
            {currentStep === 2 && importResult && (
                <div>
                    <Result
                        status={importResult.error_rows === 0 ? 'success' : 'warning'}
                        title={`${activeItem?.file.name} 导入完成`}
                        subTitle={
                            <span>
                                共 {importResult.total_rows} 条，
                                成功 <CheckCircleOutlined style={{ color: '#52c41a' }} /> {importResult.success_rows} 条，
                                跳过 {importResult.skip_rows} 条，
                                失败 <CloseCircleOutlined style={{ color: '#ff4d4f' }} /> {importResult.error_rows} 条
                            </span>
                        }
                    />
                    {importResult.errors.length > 0 && (
                        <div>
                            <h4 style={{ marginTop: 12, marginBottom: 8 }}>详细记录（共 {importResult.errors.length} 条）</h4>
                            <div style={{ maxHeight: 400, overflow: 'auto' }}>
                                <Table
                                    dataSource={importResult.errors.map((e, i) => ({ key: i, row: e.row, reason: e.reason }))}
                                    columns={[
                                        { title: '行号', dataIndex: 'row', key: 'row', width: 80 },
                                        {
                                            title: '处理详情',
                                            dataIndex: 'reason',
                                            key: 'reason',
                                            width: 500,
                                            ellipsis: true,
                                            render: (v: string) => v ? <Tooltip title={v}><span style={{ whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis', display: 'block' }}>{v}</span></Tooltip> : '-',
                                        },
                                    ]}
                                    size="small"
                                    pagination={importResult.errors.length > 20 ? { pageSize: 20 } : false}
                                    scroll={{ x: 600 }}
                                    style={{ marginTop: 8 }}
                                />
                            </div>
                        </div>
                    )}
                    <div style={{ marginTop: 24, textAlign: 'center' }}>
                        <Space>
                            {uploadItems.length > 1 && (
                                <Button onClick={() => {
                                    setImportResult(null);
                                    setCurrentStep(1);
                                }}>
                                    继续导入其余文件
                                </Button>
                            )}
                            <Button type="primary" onClick={handleClose}>
                                完成
                            </Button>
                        </Space>
                    </div>
                </div>
            )}
        </Modal>
    );
}
