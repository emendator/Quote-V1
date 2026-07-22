import { Table, Select } from 'antd';

const DB_FIELDS = [
    { value: '', label: '— 不导入 —' },
    { value: 'quick_model', label: '快查型号 *' },
    { value: 'product_model', label: '型号' },
    { value: 'product_name', label: '产品名称' },
    { value: 'brand', label: '品牌' },
    { value: 'category_level1', label: '一级品类' },
    { value: 'category_level2', label: '二级品类' },
    { value: 'category_level3', label: '三级品类' },
    { value: 'negotiation_price', label: '备货商谈价(元)' },
    { value: 'price_update', label: '报价更新' },
    { value: 'last_purchase_price', label: '上次进货价(元)' },
    { value: 'purchase_price', label: '进货价(元)' },
    { value: 'retail_price', label: '零售价(元)' },
    { value: 'new_event_price', label: '新活动价(元)' },
    { value: 'discount_rate', label: '折扣率(自动计算)' },
    { value: 'shop_url', label: '链接' },
    { value: 'bid_price', label: '投标价(元)' },
    { value: 'group_purchase_price', label: '集采价/项目(元)' },
    { value: 'price', label: '代发价(元) *' },
    { value: 'gross_weight', label: '毛重(kg)' },
    { value: 'box_spec', label: '箱规' },
    { value: 'cooperation_level', label: '合作等级' },
    { value: 'supply_status', label: '供货状态' },
    { value: 'specification', label: '规格' },
    { value: 'remark', label: '备注' },
    { value: 'shipping_fee', label: '代发运费(元)' },
    { value: 'barcode_69', label: '69码' },
    { value: 'sales_volume', label: '销量' },
    { value: 'recommendation', label: '推荐理由' },
    { value: 'parameters', label: '参数' },
    { value: 'cert_3c', label: '3C' },
    { value: 'image', label: '图片' },
];

interface Props {
    columns: string[];
    mapping: Record<string, string>;
    onChange: (mapping: Record<string, string>) => void;
}

export default function ColumnMapping({ columns, mapping, onChange }: Props) {
    const dataSource = columns.map((col, idx) => ({
        key: idx,
        column: col,
        mappedField: mapping[col] || '',
    }));

    const handleChange = (column: string, field: string) => {
        const newMapping = { ...mapping, [column]: field };
        // 如果设置为空则删除该映射
        if (!field) {
            delete newMapping[column];
        }
        onChange(newMapping);
    };

    const tableColumns = [
        {
            title: 'Excel 列名',
            dataIndex: 'column',
            key: 'column',
            width: 200,
            render: (v: string) => <strong>{v}</strong>,
        },
        {
            title: '映射到数据库字段',
            dataIndex: 'mappedField',
            key: 'mappedField',
            render: (_: string, record: { column: string; mappedField: string }) => (
                <Select
                    style={{ width: '100%' }}
                    value={record.mappedField || ''}
                    onChange={(val) => handleChange(record.column, val)}
                    options={DB_FIELDS}
                    placeholder="选择映射字段"
                />
            ),
        },
    ];

    return (
        <div className="mapping-container">
            <p style={{ marginBottom: 12, color: '#666' }}>
                请为每个 Excel 列选择对应的数据库字段。标记 <span style={{ color: '#ff4d4f' }}>*</span> 的字段为必填。
            </p>
            <Table
                columns={tableColumns}
                dataSource={dataSource}
                pagination={false}
                size="small"
                rowKey="key"
            />
        </div>
    );
}
