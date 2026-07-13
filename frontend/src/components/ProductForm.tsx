import { useEffect, useState } from 'react';
import { Modal, Form, Input, InputNumber, Upload, Button, message } from 'antd';
import { UploadOutlined, DeleteOutlined, LoadingOutlined, PlusOutlined } from '@ant-design/icons';
import type { UploadFile } from 'antd/es/upload/interface';
import type { Product } from '../types';
import { createProduct, updateProduct, uploadProductImage, deleteProductImage } from '../services/api';

interface Props {
    open: boolean;
    editingProduct: Product | null;
    onClose: () => void;
    onSuccess: () => void;
}

export default function ProductForm({ open, editingProduct, onClose, onSuccess }: Props) {
    const [form] = Form.useForm();
    const isEdit = !!editingProduct;
    const [uploading, setUploading] = useState(false);
    const [imageUrl, setImageUrl] = useState<string | null>(null);

    useEffect(() => {
        if (open) {
            if (editingProduct) {
                form.setFieldsValue(editingProduct);
                setImageUrl(editingProduct.product_image || null);
            } else {
                form.resetFields();
                setImageUrl(null);
            }
        }
    }, [open, editingProduct, form]);

    const handleImageUpload = async (file: File) => {
        if (!editingProduct) {
            message.warning('请先保存商品基本信息后再上传图片');
            return true; // 阻止上传
        }
        setUploading(true);
        try {
            const updated = await uploadProductImage(editingProduct.id, file);
            setImageUrl(updated.product_image);
            message.success('图片上传成功');
        } catch (err: unknown) {
            const msg = err instanceof Error ? err.message : '上传失败';
            message.error(msg);
        } finally {
            setUploading(false);
        }
        return false; // 阻止默认上传
    };

    const handleImageDelete = async () => {
        if (!editingProduct) return;
        try {
            await deleteProductImage(editingProduct.id);
            setImageUrl(null);
            message.success('图片已删除');
        } catch (err: unknown) {
            const msg = err instanceof Error ? err.message : '删除失败';
            message.error(msg);
        }
    };

    const handleSubmit = async () => {
        try {
            const values = await form.validateFields();
            if (isEdit && editingProduct) {
                await updateProduct(editingProduct.id, values);
                message.success('更新成功');
            } else {
                const product = await createProduct(values);
                // 如果有已选图片还未上传（首次创建时不可能，但保留逻辑）
                onSuccess();
            }
            onSuccess();
            onClose();
        } catch (err: unknown) {
            if (err instanceof Error && err.message) {
                message.error(err.message);
            }
        }
    };

    return (
        <Modal
            title={isEdit ? '编辑商品' : '新增商品'}
            open={open}
            onOk={handleSubmit}
            onCancel={onClose}
            width={700}
            destroyOnClose
            okText="保存"
            cancelText="取消"
        >
            <Form form={form} layout="vertical" style={{ marginTop: 16 }}>
                <Form.Item label="商品图片">
                    <div style={{ display: 'flex', gap: 12, alignItems: 'flex-start' }}>
                        {imageUrl ? (
                            <div style={{ position: 'relative' }}>
                                <img
                                    src={imageUrl}
                                    alt="商品图片"
                                    style={{ width: 100, height: 100, objectFit: 'cover', borderRadius: 6, border: '1px solid #d9d9d9' }}
                                />
                                <Button
                                    size="small"
                                    danger
                                    icon={<DeleteOutlined />}
                                    onClick={handleImageDelete}
                                    style={{ position: 'absolute', top: -8, right: -8 }}
                                />
                            </div>
                        ) : (
                            <Upload
                                accept="image/png,image/jpeg,image/gif,image/webp"
                                showUploadList={false}
                                beforeUpload={(file) => {
                                    handleImageUpload(file as File);
                                    return false;
                                }}
                                disabled={!isEdit}
                            >
                                <Button
                                    icon={uploading ? <LoadingOutlined /> : <UploadOutlined />}
                                    disabled={!isEdit || uploading}
                                >
                                    {uploading ? '上传中...' : '上传图片'}
                                </Button>
                            </Upload>
                        )}
                        {!isEdit && (
                            <span style={{ color: '#999', fontSize: 12, lineHeight: '32px' }}>
                                保存商品后可上传图片
                            </span>
                        )}
                    </div>
                    <div style={{ color: '#999', fontSize: 12, marginTop: 4 }}>支持 JPG / PNG / GIF / WebP 格式</div>
                </Form.Item>
                <Form.Item name="brand" label="品牌">
                    <Input placeholder="品牌" />
                </Form.Item>
                <Form.Item name="category" label="类别">
                    <Input placeholder="商品类别" />
                </Form.Item>
                <Form.Item name="product_model" label="商品型号">
                    <Input placeholder="商品型号" />
                </Form.Item>
                <Form.Item name="specification" label="规格">
                    <Input placeholder="如：500ml×24瓶/箱" />
                </Form.Item>
                <Form.Item name="jd_price" label="京东划线价(元)">
                    <InputNumber min={0} precision={2} style={{ width: '100%' }} placeholder="0.00" />
                </Form.Item>
                <Form.Item name="cost_price" label="成本价(元)">
                    <InputNumber min={0} precision={2} style={{ width: '100%' }} placeholder="0.00" />
                </Form.Item>
                <Form.Item name="price" label="代发价/报价(元)" rules={[{ required: true, message: '请输入代发价' }]}>
                    <InputNumber min={0} precision={2} style={{ width: '100%' }} placeholder="0.00" />
                </Form.Item>
                <Form.Item name="barcode_69" label="69码">
                    <Input placeholder="69码" />
                </Form.Item>
                <Form.Item name="supplier" label="供应商">
                    <Input placeholder="供应商" />
                </Form.Item>
                <Form.Item name="shop_url" label="店铺链接">
                    <Input placeholder="店铺链接（可选）" />
                </Form.Item>
                <Form.Item name="stock" label="库存">
                    <InputNumber min={0} style={{ width: '100%' }} placeholder="0" />
                </Form.Item>
                <Form.Item name="remark" label="备注">
                    <Input.TextArea rows={2} placeholder="备注信息" />
                </Form.Item>
                <Form.Item label="折扣率">
                    <Input disabled placeholder="由代发价/京东划线价自动计算" />
                </Form.Item>
            </Form>
        </Modal>
    );
}
