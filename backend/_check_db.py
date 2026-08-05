"""Check if products have image data"""
import sys; sys.path.insert(0, '.')
from app.database import sync_engine
from sqlalchemy import text

with sync_engine.connect() as conn:
    rows = conn.execute(text("SELECT id, quick_model, image IS NOT NULL AND image != '' as has_image, LENGTH(image) as img_len FROM products ORDER BY id DESC LIMIT 20")).fetchall()
    print("Latest 20 products in DB:")
    for r in rows:
        print(f"  id={r[0]}, quick_model={r[1]}, has_image={r[2]}, img_len={r[3]}")
    
    total = conn.execute(text("SELECT COUNT(*) FROM products")).scalar()
    total_with_image = conn.execute(text("SELECT COUNT(*) FROM products WHERE image IS NOT NULL AND image != ''")).scalar()
    print(f"\nTotal products: {total}")
    print(f"Total with images: {total_with_image}")
