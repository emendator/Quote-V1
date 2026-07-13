# 智能报价系统 (Smart Quotation System)

基于公司内部商品数据库的智能报价查询系统，支持通过 SKU、69 码、产品规格、价格等多种维度快速查询商品报价。

## 功能特性

- 🔍 **智能查询**：支持自然语言输入，自动识别查询意图（69码、SKU、规格、价格区间等）
- 💬 **微信群消息解析**：直接粘贴客户询价消息，自动提取商品信息
- 📊 **数据管理**：商品增删改查、分页、搜索、筛选
- 📥 **Excel 导入**：自动识别不同格式的表格列名，支持列映射配置
- 🎨 **简约界面**：基于 Ant Design 的现代化界面

## 技术栈

| 层级 | 技术 |
|------|------|
| 前端 | React 18 + TypeScript + Vite + Ant Design 5 |
| 后端 | Python FastAPI + SQLAlchemy |
| 数据库 | SQLite |

## 快速开始

### 1. 后端启动

```bash
cd backend
pip install -r requirements.txt
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

API 文档访问：<http://localhost:8000/docs>

### 2. 前端启动

```bash
cd frontend
npm install
npm run dev
```

前端访问：<http://localhost:5173>

## 项目结构

```
智能报价/
├── backend/                 # 后端
│   ├── app/
│   │   ├── main.py         # FastAPI 入口
│   │   ├── config.py       # 配置
│   │   ├── database.py     # 数据库
│   │   ├── models.py       # 数据模型
│   │   ├── schemas.py      # 请求/响应模型
│   │   ├── routers/        # API 路由
│   │   ├── services/       # 业务逻辑
│   │   └── utils/          # 工具函数
│   └── requirements.txt
├── frontend/                # 前端
│   └── src/
│       ├── components/     # 组件
│       ├── pages/          # 页面
│       ├── services/       # API 封装
│       └── types/          # 类型定义
└── README.md
```
