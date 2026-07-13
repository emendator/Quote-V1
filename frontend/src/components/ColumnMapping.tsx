import { Table, Select } from 'antd';

const DB_FIELDS = [
    { value: '', label: '— 不导入 —' },
    { value: 'brand', label: '品牌' },
    { value: 'product_image', label: '商品图片' },
    { value: 'category', label: '类别' },
    { value: 'product_model', label: '商品型号' },
    { value: 'specification', label: '规格' },
    { value: 'jd_price', label: '京东划线价(元)' },
    { value: 'cost_price', label: '成本价(元)' },
    { value: 'price', label: '代发价/报价(元) *' },
    { value: 'barcode_69', label: '69码' },
    { value: 'supplier', label: '供应商' },
    { value: 'shop_url', label: '店铺链接' },
    { value: 'stock', label: '库存' },
    { value: 'remark', label: '备注' },
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
