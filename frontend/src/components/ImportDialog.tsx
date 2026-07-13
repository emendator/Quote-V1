import { useState } from 'react';
import {
    Modal, Steps, Upload, Button, Table, Select, Radio,
    Result, Space, message, Alert,
} from 'antd';
import {
    InboxOutlined, CheckCircleOutlined, CloseCircleOutlined,
} from '@ant-design/icons';
import type { UploadFile, RcFile } from 'antd/es/upload';
import ColumnMapping from './ColumnMapping';
import { uploadFile, confirmImport } from '../services/api';
import type { UploadResult, ImportResult } from '../types';

const { Dragger } = Upload;

interface Props {
    open: boolean;
    onClose: () => void;
    onSuccess: () => void;
}

export default function ImportDialog({ open, onClose, onSuccess }: Props) {
    const [currentStep, setCurrentStep] = useState(0);
    const [file, setFile] = useState<RcFile | null>(null);
    const [uploadResult, setUploadResult] = useState<UploadResult | null>(null);
    const [mapping, setMapping] = useState<Record<string, string>>({});
    const [strategy, setStrategy] = useState('skip');
    const [importResult, setImportResult] = useState<ImportResult | null>(null);
    const [loading, setLoading] = useState(false);

    const resetState = () => {
        setCurrentStep(0);
        setFile(null);
        setUploadResult(null);
        setMapping({});
        setStrategy('skip');
        setImportResult(null);
    };

    const handleClose = () => {
        resetState();
        onClose();
    };

    const handleUpload = async (file: RcFile): Promise<false | undefined> => {
        setLoading(true);
        try {
            const result = await uploadFile(file);
            setUploadResult(result);
            setMapping(result.suggested_mapping);
            setFile(file);
            setCurrentStep(1);
            message.success('文件解析成功');
        } catch (err: unknown) {
            const msg = err instanceof Error ? err.message : '上传失败';
            message.error(msg);
            return false;
        } finally {
            setLoading(false);
        }
        return undefined;
    };

    const handleConfirmImport = async () => {
        if (!uploadResult) return;

        // 检查必填字段
        const mappedFields = Object.values(mapping);
        if (!mappedFields.includes('price')) {
            message.warning('请至少映射「代发价/报价」字段');
            return;
        }

        setLoading(true);
        try {
            const result = await confirmImport({
                file_id: uploadResult.file_id,
                column_mapping: mapping,
                duplicate_strategy: strategy,
            });
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
            width={800}
            footer={null}
            destroyOnClose
        >
            <Steps current={currentStep} items={steps} className="import-steps" />

            {/* 步骤 1：上传文件 */}
            {currentStep === 0 && (
                <div>
                    <Dragger
                        accept=".xlsx,.xls,.csv"
                        maxCount={1}
                        beforeUpload={(f) => {
                            handleUpload(f as RcFile);
                            return false;
                        }}
                        showUploadList={false}
                        disabled={loading}
                    >
                        <p className="ant-upload-drag-icon">
                            <InboxOutlined />
                        </p>
                        <p className="ant-upload-text">点击或拖拽文件到此区域上传</p>
                        <p className="ant-upload-hint">
                            支持 .xlsx / .xls / .csv 格式，最大 50MB
                        </p>
                    </Dragger>
                </div>
            )}

            {/* 步骤 2：配置列映射 */}
            {currentStep === 1 && uploadResult && (
                <div>
                    <Alert
                        message={`文件：${uploadResult.file_name} | 共 ${uploadResult.total_rows} 行数据`}
                        type="info"
                        style={{ marginBottom: 16 }}
                        showIcon
                    />
                    <ColumnMapping
                        columns={uploadResult.columns}
                        mapping={mapping}
                        onChange={setMapping}
                    />

                    {uploadResult.preview_rows.length > 0 && (
                        <div style={{ marginTop: 16 }}>
                            <h4>数据预览（前 {uploadResult.preview_rows.length} 行）</h4>
                            <Table
                                columns={uploadResult.columns.map((col) => ({ title: col, dataIndex: col, key: col, ellipsis: true }))}
                                dataSource={uploadResult.preview_rows.map((row, idx) => {
                                    const obj: Record<string, string> = { key: String(idx) };
                                    uploadResult!.columns.forEach((col, i) => {
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
                        <span style={{ marginRight: 16 }}>重复数据处理策略：</span>
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
                                确认导入
                            </Button>
                        </Space>
                    </div>
                </div>
            )}

            {/* 步骤 3：导入结果 */}
            {currentStep === 2 && importResult && (
                <div>
                    <Result
                        status={importResult.error_rows === 0 ? 'success' : 'warning'}
                        title="导入完成"
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
                        <Table
                            dataSource={importResult.errors.map((e, i) => ({ key: i, row: e.row, reason: e.reason }))}
                            columns={[
                                { title: '行号', dataIndex: 'row', key: 'row', width: 80 },
                                { title: '错误原因', dataIndex: 'reason', key: 'reason' },
                            ]}
                            size="small"
                            pagination={false}
                            style={{ marginTop: 16 }}
                        />
                    )}
                    <div style={{ marginTop: 24, textAlign: 'center' }}>
                        <Button type="primary" onClick={handleClose}>
                            完成
                        </Button>
                    </div>
                </div>
            )}
        </Modal>
    );
}
