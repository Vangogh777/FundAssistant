# 📈 基金智能助手

全栈 Web 应用：管理基金持仓、实时估值、AI 智能分析、市场行情，支持多模型 AI 交易建议与多渠道定投提醒。

## ✨ 功能

| 模块 | 功能 |
|------|------|
| 📊 估值看板 | 总资产、今日盈亏、累计盈亏、收益折线图 + 沪深300对比 |
| 📋 持仓管理 | 基金搜索/添加、新买入自动算份额、原本持有模式、批量同步、修改历史 |
| 🤖 AI 分析 | 快速预测(1/3/5/7天)、AI 深度分析(OpenAI/DeepSeek/Claude)、持仓穿透分析 |
| 📈 市场行情 | 大盘指数、北向资金、主力流向、板块排行、财经快讯 |
| ⚙️ 设置 | API Key 配置、邮件/飞书/微信/QQ 通知渠道、定投计划 |
| 📷 OCR | 支付宝/微信截图识别、批量同步持仓 |
| 🌙 主题 | 深色科技蓝 / 浅色简约 一键切换 |
| 📱 移动端 | 响应式布局，手机浏览器可用 |

## 🚀 快速启动

### 后端

```bash
cd backend
pip install -r requirements.txt
python run.py          # http://localhost:8000
```

### 前端

```bash
cd frontend
npm install
npm run dev -- --host  # http://localhost:5173
```

手机同 WiFi 下访问 `http://<笔记本IP>:5173`

## 🛠 技术栈

| 层 | 技术 |
|---|------|
| 后端框架 | FastAPI (Python) |
| ORM | SQLAlchemy 2.0 (async) |
| 数据库 | SQLite |
| 前端 | React 18 + Vite + Ant Design 5 |
| 图表 | Recharts |
| AI | OpenAI / DeepSeek / Claude API |
| OCR | Tesseract CLI |
| 行情数据 | 东方财富 / 天天基金 |

## 📦 项目结构

```
fund-assistant/
├── backend/
│   ├── app/
│   │   ├── models/        # 10张数据表
│   │   ├── routers/       # 7组API路由
│   │   ├── services/      # 爬虫/估值/AI/通知/调度
│   │   └── utils/         # JWT工具
│   └── requirements.txt
└── frontend/
    └── src/
        ├── pages/          # 6个页面
        ├── components/     # 布局/弹窗
        ├── api/            # Axios 封装
        └── theme/          # 深浅主题
```

## 📡 数据源

- 基金实时估值：天天基金 `fundgz.1234567.com.cn`
- 历史净值：东方财富 `api.fund.eastmoney.com`
- 大盘指数：东方财富 `push2.eastmoney.com`
- 基金持仓穿透：东方财富 `fundf10.eastmoney.com`
- 北向资金：东方财富

## 🤖 AI 模型

| 模型 | 配置方式 |
|------|---------|
| DeepSeek V4 Flash / Pro | 设置页填写 DeepSeek API Key |
| OpenAI GPT-4o | 设置页填写 OpenAI API Key |
| Claude 3.5 Sonnet | 设置页填写 Claude API Key |

未配置 Key 时使用本地技术分析（动量/波动率/夏普比率/回撤/胜率），无需联网也可使用。

## 📱 手机访问

笔记本和手机连同一 WiFi，手机浏览器访问：

```
http://<笔记本局域网IP>:5173
```

笔记本 IP 查询：`ifconfig | grep "inet "`

## 📄 License

MIT
