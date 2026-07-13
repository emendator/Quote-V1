import requests

r = requests.get('http://127.0.0.1:8000/api/products?page_size=5')
data = r.json()
total = data['data']['total']
print('数据库商品总数:', total)
print('前5条:')
for item in data['data']['items']:
    img = item.get('product_image', '')
    print(f'  ID:{item["id"]} {item["brand"]} {item["product_model"]} 图片:{img[:60] if img else "(空)"}')
