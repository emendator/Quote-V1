import requests
import json

# 上传文件
url = 'http://127.0.0.1:8000/api/import/upload'
with open(r'd:\learn\code\work\智能报价\backend\uploads\3ce64bbb-c310-4bfd-b613-0be5520db2e7.xlsx', 'rb') as f:
    files = {'file': f}
    r = requests.post(url, files=files)
data = r.json()
print('上传成功, file_id:', data['data']['file_id'])
file_id = data['data']['file_id']

# 确认导入
import_url = 'http://127.0.0.1:8000/api/import/confirm'
payload = {
    'file_id': file_id,
    'column_mapping': {
        '品牌': 'brand', '商品图片': 'product_image', '类别': 'category',
        '商品型号': 'product_model', '规格': 'specification',
        '京东划线价(元)': 'jd_price', '成本价(元)': 'cost_price',
        '代发价(元)': 'price', '69码': 'barcode_69',
        '供应商': 'supplier', '店铺链接': 'shop_url',
        '库存': 'stock', '备注': 'remark'
    },
    'duplicate_strategy': 'skip'
}
r2 = requests.post(import_url, json=payload)
result = r2.json()
print('\n完整响应:', json.dumps(result, ensure_ascii=False, indent=2))
d = result.get('data')
if d:
    print('\n导入结果:')
    print('  总行数:', d['total_rows'])
    print('  成功:', d['success_rows'])
    print('  跳过:', d['skip_rows'])
    print('  失败:', d['error_rows'])
    if d.get('errors'):
        for e in d['errors'][:3]:
            print('  错误: 行', e['row'], '-', e['reason'])
