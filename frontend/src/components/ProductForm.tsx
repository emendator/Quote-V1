import { useEffect } from 'react';
import { Modal, Form, Input, InputNumber, Select, message } from 'antd';
import type { Product } from '../types';
import { createProduct, updateProduct } from '../services/api';

interface Props {
    open: boolean;
    editingProduct: Product | null;
    onClose: () => void;
    onSuccess: () => void;
}

export default function ProductForm({ open, editingProduct, onClose, onSuccess }: Props) {
    const [form] = Form.useForm();
    const isEdit = !!editingProduct;

    useEffect(() => {
        if (open) {
            if (editingProduct) {
                form.setFieldsValue(editingProduct);
            } else {
                form.resetFields();
            }
        }
    }, [open, editingProduct, form]);

    const handleSubmit = async () => {
        try {
            const values = await form.validateFields();
            if (isEdit && editingProduct) {
                await updateProduct(editingProduct.id, values);
                message.success('更新成功');
            } else {
                await createProduct(values);
                message.success('新增成功');
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
            width={800}
            destroyOnClose
            okText="保存"
            cancelText="取消"
        >
            <Form form={form} layout="vertical" style={{ marginTop: 16 }}>
                <Form.Item name="quick_model" label="快查型号" rules={[{ required: true, message: '请输入快查型号' }]}>
                    <Input placeholder="快查型号（必填，去重依据）" />
                </Form.Item>
                <Form.Item name="product_model" label="型号" rules={[{ required: true, message: '请输入型号' }]}>
                    <Input placeholder="型号（必填）" />
                </Form.Item>
                <Form.Item name="product_name" label="产品名称">
                    <Input placeholder="产品名称" />
                </Form.Item>
                <Form.Item name="brand" label="品牌">
                    <Input placeholder="品牌" />
                </Form.Item>
                <Form.Item name="category_level1" label="一级品类">
                    <Input placeholder="一级品类" />
                </Form.Item>
                <Form.Item name="category_level2" label="二级品类">
                    <Input placeholder="二级品类" />
                </Form.Item>
                <Form.Item name="negotiation_price" label="备货商谈价(元)">
                    <InputNumber min={0} precision={2} style={{ width: '100%' }} placeholder="0.00" />
                </Form.Item>
                <Form.Item name="price_update" label="报价更新">
                    <Input placeholder="报价更新" />
                </Form.Item>
                <Form.Item name="last_purchase_price" label="上次进货价(元)">
                    <InputNumber min={0} precision={2} style={{ width: '100%' }} placeholder="0.00" />
                </Form.Item>
                <Form.Item name="purchase_price" label="进货价(元)">
                    <InputNumber min={0} precision={2} style={{ width: '100%' }} placeholder="0.00" />
                </Form.Item>
                <Form.Item name="retail_price" label="零售价(元)">
                    <InputNumber min={0} precision={2} style={{ width: '100%' }} placeholder="0.00" />
                </Form.Item>
                <Form.Item label="折扣率">
                    <Input disabled placeholder="由代发价/零售价自动计算" />
                </Form.Item>
                <Form.Item name="new_event_price" label="新活动价(元)">
                    <InputNumber min={0} precision={2} style={{ width: '100%' }} placeholder="0.00" />
                </Form.Item>
                <Form.Item name="shop_url" label="链接">
                    <Input placeholder="链接（可选）" />
                </Form.Item>
                <Form.Item name="bid_price" label="投标价(元)">
                    <InputNumber min={0} precision={2} style={{ width: '100%' }} placeholder="0.00" />
                </Form.Item>
                <Form.Item name="group_purchase_price" label="集采价/项目(元)">
                    <InputNumber min={0} precision={2} style={{ width: '100%' }} placeholder="0.00" />
                </Form.Item>
                <Form.Item name="price" label="代发价(元)" rules={[{ required: true, message: '请输入代发价' }]}>
                    <InputNumber min={0} precision={2} style={{ width: '100%' }} placeholder="0.00" />
                </Form.Item>
                <Form.Item name="gross_weight" label="毛重(kg)">
                    <InputNumber min={0} precision={2} style={{ width: '100%' }} placeholder="0.00" />
                </Form.Item>
                <Form.Item name="box_spec" label="箱规">
                    <Input placeholder="箱规" />
                </Form.Item>
                <Form.Item name="cooperation_level" label="合作等级">
                    <Input placeholder="合作等级" />
                </Form.Item>
                <Form.Item name="supply_status" label="供货状态">
                    <Input placeholder="供货状态" />
                </Form.Item>
                <Form.Item name="specification" label="规格">
                    <Input placeholder="如：500ml×24瓶/箱" />
                </Form.Item>
                <Form.Item name="remark" label="备注">
                    <Input.TextArea rows={2} placeholder="备注信息" />
                </Form.Item>
                <Form.Item name="shipping_fee" label="代发运费(元)">
                    <InputNumber min={0} precision={2} style={{ width: '100%' }} placeholder="0.00" />
                </Form.Item>
                <Form.Item name="barcode_69" label="69码">
                    <Input placeholder="69码" />
                </Form.Item>
                <Form.Item name="sales_volume" label="销量">
                    <InputNumber min={0} style={{ width: '100%' }} placeholder="0" />
                </Form.Item>
                <Form.Item name="recommendation" label="推荐理由">
                    <Input.TextArea rows={2} placeholder="推荐理由" />
                </Form.Item>
                <Form.Item name="parameters" label="参数">
                    <Input.TextArea rows={2} placeholder="商品参数" />
                </Form.Item>
                <Form.Item name="cert_3c" label="3C">
                    <Input placeholder="3C认证编号" />
                </Form.Item>
                <Form.Item name="image" label="产品图片">
                    <Input.TextArea rows={2} placeholder="粘贴图片Base64编码或URL，也可通过Excel导入自动提取" />
                </Form.Item>
            </Form>
        </Modal>
    );
}
