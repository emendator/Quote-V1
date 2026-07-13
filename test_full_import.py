import requests, json, time, sys, os

# Wait for backend to be ready
for i in range(10):
    try:
        r = requests.get('http://127.0.0.1:8000/api/health', timeout=3)
        if r.status_code == 200:
            print('Backend ready')
            break
    except:
        pass
    time.sleep(2)

# Upload file
file_path = r'd:\learn\code\work\智能报价\backend\uploads\3ce64bbb-c310-4bfd-b613-0be5520db2e7.xlsx'
print('Uploading file...')
with open(file_path, 'rb') as f:
    r = requests.post('http://127.0.0.1:8000/api/import/upload', files={'file': f})
data = r.json()
file_id = data['data']['file_id']
print('file_id:', file_id)

# Confirm import
print('Confirming import...')
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
r2 = requests.post('http://127.0.0.1:8000/api/import/confirm', json=payload, timeout=60)
result = r2.json()
print('Import code:', result.get('code'))
print('Import message:', result.get('message'))
d = result.get('data')
if d:
    print('total:', d['total_rows'], 'success:', d['success_rows'])
    print('skip:', d['skip_rows'], 'error:', d['error_rows'])
    if d.get('errors'):
        for e in d['errors'][:3]:
            print('  Error:', e)

# Check products with images
print('\nChecking imported products:')
r3 = requests.get('http://127.0.0.1:8000/api/products?page_size=10')
items = r3.json()['data']['items']
print('Total products:', r3.json()['data']['total'])
has_image = 0
for item in items:
    img = item.get('product_image', '')
    status = f'ID:{item["id"]} {item["brand"]} {item["product_model"]}'
    if img:
        status += f'  IMAGE:{img[:60]}'
        has_image += 1
    else:
        status += '  (no image)'
    print(' ', status)
print(f'\