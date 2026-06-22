# 📈 基金智能助手 (Fund Assistant)

> 全栈基金投资辅助工具 — 持仓管理 · 实时估值 · AI 分析 · 市场行情 · 定投提醒

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue)](https://www.python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-%2300a86b)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React-18.3-%2361dafb)](https://react.dev)
[![Ant Design](https://img.shields.io/badge/Ant%20Design-5.20-%23017fff)](https://ant.design)
[![License](https://img.shields.io/badge/License-MIT-green)](LICENSE)

---

## 📸 界面预览

| 深色模式 | 浅色模式 |
|---------|---------|
| 估值看板、持仓管理、AI 分析、市场行情、设置 | 一键切换 |

---

## ✨ 功能总览

### 📊 估值看板
- 总资产、今日盈亏、累计盈亏实时计算
- 收益/市值走势折线图（含沪深 300 基准对比）
- 持仓盈亏分布饼图

### 📋 持仓管理
- 基金搜索添加（天天基金接口）
- 新买入自动计算份额 / 原本持有两种模式
- 批量同步实时估值
- 修改持仓历史记录

### 🤖 AI 智能分析
- **快速预测**：1/3/5/7 天价格走势预测
- **AI 深度分析**：多模型支持
  - OpenAI GPT-4o
  - DeepSeek V4 Flash / Pro
  - Claude 3.5 Sonnet
- **持仓穿透分析**：穿透基金持仓，分析行业分布与重叠度
- **本地兜底**：未配置 AI Key 时自动使用技术分析（动量、波动率、夏普比率、最大回撤）

### 📈 市场行情
- 大盘指数实时行情
- 北向资金流向
- 主力资金流向
- 板块涨跌排行
- 财经快讯

### ⚙️ 系统设置
- API Key 管理（OpenAI / DeepSeek / Claude）
- 通知渠道配置（邮件 / 飞书 / 微信 / QQ）
- 定投计划管理
- 深色/浅色主题切换

### 📷 OCR 识别同步
- 支付宝基金截图识别
- 微信基金截图识别
- CSV 文件导入
- 批量同步到持仓

---

## 🚀 快速启动

### 前置要求

| 工具 | 版本 |
|------|------|
| Python | 3.10+ |
| Node.js | 18+ |
| npm | 9+ |

### 1️⃣ 克隆仓库

```bash
git clone https://github.com/Vangogh777/FundAssistant.git
cd FundAssistant
```

### 2️⃣ 启动后端

```bash
cd fund-assistant/backend
pip install -r requirements.txt
python run.py
```

后端运行在 **http://localhost:8000**，自动创建 SQLite 数据库。

> 可通过 `.env` 文件配置密钥、数据库路径等：
> ```env
> SECRET_KEY=your-secret-key-change-in-production
> DATABASE_URL=sqlite+aiosqlite:///./fund_assistant.db
> ```

### 3️⃣ 启动前端

```bash
cd fund-assistant/frontend
npm install
npm run dev -- --host
```

前端运行在 **http://localhost:5173**，Vite 自动将 `/api` 请求代理到后端。

### 4️⃣ 手机访问

笔记本与手机连接同一 WiFi：

```
http://<笔记本局域网IP>:5173
```

查询笔记本 IP：`ifconfig | grep "inet "`（macOS / Linux）

---

## 🛠 技术栈

### 后端

| 技术 | 用途 |
|------|------|
| **FastAPI** | Web 框架 (Async) |
| **SQLAlchemy 2.0** | Async ORM |
| **SQLite + aiosqlite** | 数据库 |
| **APScheduler** | 定时任务（定投/行情刷新） |
| **python-jose** | JWT 认证 |
| **passlib + bcrypt** | 密码哈希 |
| **httpx / beautifulsoup4** | 基金数据爬取 |
| **openai** | AI 模型调用 |

### 前端

| 技术 | 用途 |
|------|------|
| **React 18** | UI 框架 |
| **Vite 5** | 构建工具 |
| **Ant Design 5** | UI 组件库 |
| **Recharts** | 图表绘制 |
| **Axios** | HTTP 客户端 |
| **React Router 6** | 路由管理 |
| **dayjs** | 日期处理 |

---

## 📁 项目结构

```
fund-assistant/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI 入口
│   │   ├── config.py            # Pydantic 配置
│   │   ├── database.py          # 数据库引擎 & 会话
│   │   ├── models/              # SQLAlchemy 模型
│   │   │   ├── user.py          # 用户
│   │   │   ├── fund.py          # 基金信息
│   │   │   ├── nav.py           # 净值数据
│   │   │   ├── portfolio.py     # 持仓
│   │   │   ├── dividend.py      # 分红
│   │   │   ├── drip.py          # 定投计划
│   │   │   ├── notification.py  # 通知渠道 + 日志
│   │   │   ├── market.py        # 行情
│   │   │   └── history.py       # 操作历史
│   │   ├── routers/             # API 路由
│   │   │   ├── auth.py          # 认证
│   │   │   ├── funds.py         # 基金数据
│   │   │   ├── portfolio.py     # 持仓管理
│   │   │   ├── market.py        # 市场行情
│   │   │   ├── analysis.py      # AI 分析
│   │   │   ├── drip.py          # 定投
│   │   │   └── ocr.py           # OCR 识别
│   │   ├── schemas/             # Pydantic 请求/响应模型
│   │   ├── services/            # 业务逻辑
│   │   │   ├── fund_crawler.py  # 天天基金爬虫
│   │   │   ├── valuation.py     # 技术分析
│   │   │   ├── ai_analyzer.py   # AI 多模型集成
│   │   │   ├── holdings_analysis.py  # 持仓穿透
│   │   │   ├── notifier.py      # 多渠道通知
│   │   │   └── scheduler.py     # 定时任务
│   │   └── utils/
│   │       └── auth.py          # JWT 工具
│   ├── requirements.txt
│   ├── run.py
│   └── .env                     # 环境配置（不提交）
└── frontend/
    └── src/
        ├── main.tsx             # 入口
        ├── App.tsx              # 路由 + 主题 + 认证
        ├── pages/               # 页面组件
        │   ├── Login.tsx / Register.tsx
        │   ├── Dashboard.tsx    # 估值看板
        │   ├── Portfolio.tsx    # 持仓管理
        │   ├── Analysis.tsx     # AI 分析
        │   ├── Market.tsx       # 市场行情
        │   └── Settings.tsx     # 设置
        ├── components/          # 通用组件
        │   ├── AppLayout.tsx    # 布局导航
        │   └── SyncModal.tsx    # OCR 同步弹窗
        ├── api/                 # API 客户端
        │   ├── client.ts        # Axios + JWT 拦截
        │   └── fund.ts          # 基金相关 API
        ├── hooks/
        │   └── useAuth.ts       # 认证上下文
        └── theme/
            └── useTheme.ts      # 主题切换
```

---

## 📡 数据源说明

本工具使用以下公开数据接口，**无需任何 API Key**：

| 数据 | 来源 |
|------|------|
| 基金实时估值 | 天天基金 `fundgz.1234567.com.cn` |
| 历史净值 | 东方财富 `api.fund.eastmoney.com` |
| 大盘指数 | 东方财富 `push2.eastmoney.com` |
| 基金持仓 | 东方财富 `fundf10.eastmoney.com` |
| 北向资金 | 东方财富 |

> ⚠️ 以上接口为公开数据，仅供个人学习与研究使用。请勿高频请求。

---

## 🤖 AI 模型配置

在 **设置页面** 填写 API Key 即可启用 AI 分析：

| 模型 | 所需 Key | 特点 |
|------|---------|------|
| **DeepSeek V4 Flash** | DeepSeek API Key | 快速、性价比高 |
| **DeepSeek V4 Pro** | DeepSeek API Key | 深度分析 |
| **OpenAI GPT-4o** | OpenAI API Key | 综合能力强 |
| **Claude 3.5 Sonnet** | Anthropic API Key | 金融分析优秀 |

> 💡 不配置任何 Key 时，系统会自动使用本地技术分析（动量、波动率、夏普比率、回撤、胜率等），无需联网也可使用全部功能。

---

## 📱 API 概览

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/auth/register` | POST | 注册 |
| `/api/auth/login` | POST | 登录 |
| `/api/auth/refresh` | POST | 刷新 Token |
| `/api/auth/me` | GET/PUT | 用户信息 |
| `/api/funds/search` | GET | 搜索基金 |
| `/api/funds/{code}` | GET | 基金详情 |
| `/api/portfolio` | GET/POST | 持仓列表/添加 |
| `/api/portfolio/{id}` | PUT/DELETE | 更新/删除持仓 |
| `/api/portfolio/sync` | POST | 批量同步估值 |
| `/api/market/indices` | GET | 大盘指数 |
| `/api/market/money-flow` | GET | 资金流向 |
| `/api/analysis/predict` | POST | 快速预测 |
| `/api/analysis/ai-report` | POST | AI 深度分析 |
| `/api/analysis/holdings` | GET | 持仓穿透 |
| `/api/drip` | GET/POST | 定投计划 |
| `/api/ocr` | POST | 截图识别 |
| `/api/health` | GET | 健康检查 |

---

## 📦 依赖安装

### 后端 (Python)

```bash
cd fund-assistant/backend
pip install -r requirements.txt
```

**requirements.txt 包含：**

```
fastapi              # Web 框架
uvicorn              # ASGI 服务器
sqlalchemy           # ORM
aiosqlite            # SQLite 异步驱动
pydantic             # 数据验证
pydantic-settings    # 配置管理
python-jose          # JWT
passlib              # 密码哈希
python-multipart     # 文件上传
httpx                # HTTP 客户端
apscheduler          # 定时任务
beautifulsoup4       # HTML 解析
lxml                 # XML 解析器
openai               # AI API
```

### 前端 (Node.js)

```bash
cd fund-assistant/frontend
npm install
```

**主要依赖：**

- `react` + `react-dom` — 核心框架
- `react-router-dom` — 路由
- `antd` + `@ant-design/icons` — UI 组件
- `axios` — HTTP 客户端
- `recharts` — 图表
- `dayjs` — 日期处理

---

## 🔧 常见问题

### Q: 登录后提示"用户名或密码错误"？
A: 首次使用请先注册账号，注册成功后自动登录。

### Q: 手机无法访问？
A: 确保手机和笔记本在同一 WiFi，Vite 以 `--host` 参数启动。

### Q: 基金数据不更新？
A: 实时估值仅在交易时段（工作日 9:30-15:00）提供。

### Q: 如何修改数据库位置？
A: 在 `.env` 中设置 `DATABASE_URL`，支持 SQLite / MySQL / PostgreSQL。

---

## 📄 License

MIT License — 自由使用、修改和分发。

---

**⭐ 如果这个项目对你有帮助，欢迎给个 Star！**
