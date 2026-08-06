"""验证：无账号公司自动清理逻辑（cleanup_orphan_companies）

在副本数据库上测试，不影响真实 data.db。
场景：
  1. 公司A（有用户绑定）→ 应保留
  2. 公司B（无任何用户绑定，但有业务数据）→ 应连同业务数据一起删除
  3. 公司C（无任何用户绑定，且无业务数据）→ 应删除
  4. company_id=0 的脏数据（不属于任何公司）→ 不应被误删
"""
import os
import sys
import shutil

# 使用临时副本数据库（必须在导入 app.database 前设置环境变量）
TEST_DB = os.path.join(os.path.dirname(__file__), "..", "data", "data_test_orphan.db")
TEST_DB = os.path.abspath(TEST_DB)
if os.path.exists(TEST_DB):
    os.remove(TEST_DB)
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{TEST_DB}"
os.environ["SYNC_DATABASE_URL"] = f"sqlite:///{TEST_DB}"

sys.path.insert(0, os.path.dirname(__file__))

import asyncio
from sqlalchemy import text

from app.database import init_db, sync_engine, AsyncSessionLocal
from app.services.company_service import cleanup_orphan_companies


async def setup():
    """初始化 DB 并构造测试数据"""
    await init_db()
    async with AsyncSessionLocal() as s:
        from app.models import User, Company, Product, SolutionPlan
        from app.utils.auth_utils import hash_password
        from app.utils.crypto_utils import encrypt_username, hash_username

        # 公司A（管理员 adminA 绑定，用户 uA 绑定）→ 保留
        ca = Company(company_name="公司A", password_hash=hash_password("pass123"), created_by=0)
        s.add(ca); await s.flush()
        # 公司B（无用户绑定，但有业务数据）→ 应删除
        cb = Company(company_name="公司B", password_hash=hash_password("pass123"), created_by=0)
        s.add(cb); await s.flush()
        # 公司C（无用户绑定，无业务数据）→ 应删除
        cc = Company(company_name="公司C", password_hash=hash_password("pass123"), created_by=0)
        s.add(cc); await s.flush()

        # 用户 adminA 绑定公司A
        u = User(
            username=encrypt_username("adminA"), username_hash=hash_username("adminA"),
            password_hash=hash_password("***REMOVED-PASSWORD***"), email="a@a.com", role="admin",
            company_id=ca.id, company_name="公司A",
        )
        s.add(u); await s.flush()

        # 公司A 的产品（应保留）
        s.add(Product(company_id=ca.id, company_name="公司A", quick_model="QA-001", price=10))
        # 公司B 的产品（应随公司B 删除）
        s.add(Product(company_id=cb.id, company_name="公司B", quick_model="QB-001", price=20))
        # 公司B 的方案+明细（应随公司B 删除）
        pb = SolutionPlan(company_id=cb.id, company_name="公司B", owner_id=0, name="B方案")
        s.add(pb); await s.flush()
        from app.models import SolutionItem
        s.add(SolutionItem(plan_id=pb.id, product_id=1, quick_model="QB-001"))
        # 公司B 的导入日志（应随公司B 删除）
        from app.models import ImportLog
        s.add(ImportLog(company_id=cb.id, company_name="公司B", file_name="b.xlsx"))
        # company_id=0 的脏数据（不属于任何公司，不应误删）
        s.add(Product(company_id=0, company_name="", quick_model="ZERO-001", price=1))
        await s.commit()


def run():
    with sync_engine.connect() as conn:
        before_companies = conn.execute(text("SELECT COUNT(*) FROM companies")).scalar()
        before_products = conn.execute(text("SELECT COUNT(*) FROM products")).scalar()
        print(f"[前] companies={before_companies}, products={before_products}")

        removed = cleanup_orphan_companies(conn)
        conn.commit()
        print(f"[清理] 删除公司: {removed}")

        # 验证
        names = [r[0] for r in conn.execute(text("SELECT company_name FROM companies")).fetchall()]
        print(f"[后] companies={names}")

        prods = conn.execute(text("SELECT quick_model FROM products ORDER BY id")).fetchall()
        print(f"[后] products={[p[0] for p in prods]}")

        plans = conn.execute(text("SELECT COUNT(*) FROM solution_plans")).scalar()
        items = conn.execute(text("SELECT COUNT(*) FROM solution_items")).scalar()
        logs = conn.execute(text("SELECT COUNT(*) FROM import_logs")).scalar()
        print(f"[后] solution_plans={plans}, solution_items={items}, import_logs={logs}")

        # 断言
        assert "公司A" in names, "公司A 应保留"
        assert "公司B" not in names, "公司B 应被删除"
        assert "公司C" not in names, "公司C 应被删除"
        assert set(removed) == {"公司B", "公司C"}, f"应删除 公司B/公司C，实际 {removed}"
        assert [p[0] for p in prods] == ["QA-001", "ZERO-001"], "公司B 产品应删除、公司A 产品与 company_id=0 脏数据应保留"
        assert plans == 0 and items == 0 and logs == 0, "公司B 的方案/明细/导入日志应删除"
        print("\n✅ 全部断言通过：无账号公司及其业务数据被删除，有账号公司与脏数据保留")


if __name__ == "__main__":
    asyncio.run(setup())
    run()
    # 清理临时副本
    try:
        os.remove(TEST_DB)
        print("临时副本已删除")
    except Exception as e:
        print(f"临时副本删除跳过（句柄未释放，可手动删除 {TEST_DB}）: {e}")
