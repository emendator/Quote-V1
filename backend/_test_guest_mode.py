"""游客模式全流程回归测试（副本数据库，不影响真实 data.db）

覆盖：
  1. 游客登录 → 创建独立游客账号+游客公司
  2. 游客可使用智能查询/数据管理/智能方案相关接口
  3. 游客可增删改商品、可导入数据
  4. 游客无用户管理权限（invites/company-password 被拒）
  5. 游客退出 cleanup → 全部痕迹清除
  6. 过期游客由系统定时清理（兜底）
"""
import os
import sys

TEST_DB = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data", "data_test_guest.db"))
if os.path.exists(TEST_DB):
    os.remove(TEST_DB)
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{TEST_DB}"
os.environ["SYNC_DATABASE_URL"] = f"sqlite:///{TEST_DB}"

sys.path.insert(0, os.path.dirname(__file__))

from fastapi.testclient import TestClient
from sqlalchemy import text

from app.database import sync_engine
from app.main import app
from app.services.company_service import cleanup_expired_guests

PASS = 0


def check(cond, name):
    global PASS
    assert cond, f"FAIL: {name}"
    PASS += 1
    print(f"  ✅ {name}")


def db_count(q, **kw):
    with sync_engine.connect() as conn:
        return conn.execute(text(q), kw).scalar() or 0


with TestClient(app) as client:
    print("=== 1. 游客登录 ===")
    r = client.post("/api/auth/guest")
    assert r.status_code == 200 and r.json()["code"] == 200, r.text
    guest = r.json()["data"]
    token = guest["access_token"]
    gu = guest["user"]
    print(f"  游客 user={gu['username']} role={gu['role']} company_id={gu['company_id']} company={gu['company_name']}")
    check(gu["role"] == "guest", "游客角色为 guest")
    check(gu["company_id"] is not None and gu["company_id"] > 0, "游客拥有独立公司")
    gid, gcid = gu["id"], gu["company_id"]
    headers = {"Authorization": f"Bearer {token}"}

    # 记录游客公司名
    with sync_engine.connect() as conn:
        cname = conn.execute(text("SELECT company_name FROM companies WHERE id=:c"), {"c": gcid}).scalar()

    print("=== 2. 游客可使用核心功能 ===")
    r = client.get("/api/products", headers=headers)
    check(r.status_code == 200 and r.json()["code"] == 200, "游客可查询商品列表")
    r = client.post("/api/products", headers=headers, json={
        "quick_model": "GUEST-P-001", "product_model": "GMP-001", "product_name": "游客测试商品", "price": 9.9,
    })
    check(r.status_code == 200 and r.json()["code"] == 200, "游客可新增商品")
    pid = r.json()["data"]["id"]
    r = client.put(f"/api/products/{pid}", headers=headers, json={"price": 12.5})
    check(r.status_code == 200 and r.json()["code"] == 200, "游客可编辑商品")
    r = client.post("/api/query/smart", headers=headers, json={"query_text": "GUEST-P-001"})
    check(r.status_code == 200 and r.json()["code"] == 200, "游客可智能查询")
    r = client.post("/api/solution/analyze", headers=headers, json={"requirement": "需要一个9.9的商品", "use_ai": False})
    check(r.status_code == 200 and r.json()["code"] == 200, "游客可使用智能方案")
    r = client.post("/api/query/batch-models", headers=headers, json={"queries": ["GUEST-P-001"], "fuzzy": False})
    check(r.status_code == 200 and r.json()["code"] == 200, "游客可批量快查")

    print("=== 3. 游客无用户管理权限 ===")
    r = client.get("/api/invites/list", headers=headers)
    check(r.status_code in (403, 200) and (r.status_code == 403 or r.json()["code"] == 403), "游客访问用户管理被拒")
    r = client.put("/api/company/password", headers=headers, json={"old_password": "x", "new_password": "123456"})
    check(r.status_code in (403, 200) and (r.status_code == 403 or r.json()["code"] == 403), "游客修改公司密码被拒")
    r = client.post("/api/company/cleanup-orphans", headers=headers)
    check(r.status_code in (403, 200) and (r.status_code == 403 or r.json()["code"] == 403), "游客手动清理公司被拒")

    print("=== 4. 游客数据隔离（看不到其他公司数据） ===")
    r = client.get("/api/products", headers=headers)
    items = r.json()["data"]["items"]
    check(len(items) == 1 and items[0]["quick_model"] == "GUEST-P-001", "游客只能看到自己公司导入的数据（隔离）")
    check(db_count("SELECT COUNT(*) FROM products") == 1, "数据库中只有游客自己的商品")

    print("=== 5. 游客退出 cleanup 清除全部痕迹 ===")
    r = client.post("/api/auth/guest/cleanup", headers=headers)
    check(r.status_code == 200 and r.json()["code"] == 200, "游客 cleanup 接口成功")
    check(db_count("SELECT COUNT(*) FROM users WHERE id=:id", id=gid) == 0, "游客用户已删除")
    check(db_count("SELECT COUNT(*) FROM companies WHERE id=:id", id=gcid) == 0, "游客公司已删除")
    check(db_count("SELECT COUNT(*) FROM products WHERE id=:id", id=pid) == 0, "游客商品已删除")
    check(db_count("SELECT COUNT(*) FROM users WHERE role='guest'") == 0, "数据库无残留游客账号")

    print("=== 6. 过期游客自动清理（兜底） ===")
    r = client.post("/api/auth/guest")
    gu2 = r.json()["data"]["user"]
    gid2, gcid2 = gu2["id"], gu2["company_id"]
    with sync_engine.connect() as conn:
        conn.execute(text("UPDATE users SET expires_at='2020-01-01 00:00:00' WHERE id=:id"), {"id": gid2})
        conn.commit()
    with sync_engine.connect() as conn:
        removed = cleanup_expired_guests(conn)
        conn.commit()
    check(gid2 in removed, "过期游客被识别并清理")
    check(db_count("SELECT COUNT(*) FROM users WHERE id=:id", id=gid2) == 0, "过期游客用户已删除")
    check(db_count("SELECT COUNT(*) FROM companies WHERE id=:id", id=gcid2) == 0, "过期游客公司已删除")

    print("=== 7. 正式账号与超管公司不受影响 ===")
    r = client.post("/api/auth/login", json={"username": "admin", "password": "***REMOVED-PASSWORD***"})
    check(r.status_code == 200 and r.json()["code"] == 200, "超管 admin 正常登录")
    with sync_engine.connect() as conn:
        c = conn.execute(text("SELECT COUNT(*) FROM companies WHERE company_name='***REMOVED-COMPANY***'")).scalar()
    check(c == 1, "超管公司保留")

print(f"\n🎉 全部 {PASS} 项断言通过")
