"""
AI 智能分析引擎
- 多模型适配器：OpenAI / DeepSeek / Claude
- 持仓综合分析报告
- 1-7天涨跌预测（消息面+技术面+趋势）
- 回测分析
- 可信度评估
"""
import json
from typing import Optional, AsyncIterator
from openai import AsyncOpenAI

from app.services.fund_crawler import fetch_fund_estimate, fetch_fund_detail, fetch_nav_history
from app.services.valuation import predict_trend, backtest_position

# ============================================================
# 模型配置
# ============================================================
MODEL_CONFIGS = {
    "openai": {
        "name": "OpenAI GPT-4o",
        "base_url": "https://api.openai.com/v1",
        "model_id": "gpt-4o",
        "default_key_label": "openai",
        "variants": None,  # 无子模型
    },
    "deepseek-v4-flash": {
        "name": "DeepSeek V4 Flash",
        "base_url": "https://api.deepseek.com",
        "model_id": "deepseek-chat",
        "default_key_label": "deepseek",
        "variants": None,
    },
    "deepseek-v4-pro": {
        "name": "DeepSeek V4 Pro",
        "base_url": "https://api.deepseek.com",
        "model_id": "deepseek-reasoner",
        "default_key_label": "deepseek",
        "variants": None,
    },
    "claude": {
        "name": "Claude 3.5 Sonnet",
        "base_url": "https://api.anthropic.com/v1",
        "model_id": "claude-3-5-sonnet-20241022",
        "default_key_label": "claude",
        "variants": None,
    },
}

# 按提供商分组（前端用）
MODEL_PROVIDERS = [
    {
        "provider": "openai",
        "label": "OpenAI",
        "models": [
            {"key": "openai", "label": "GPT-4o"},
        ],
    },
    {
        "provider": "deepseek",
        "label": "DeepSeek",
        "models": [
            {"key": "deepseek-v4-flash", "label": "DeepSeek V4 Flash（快速）"},
            {"key": "deepseek-v4-pro", "label": "DeepSeek V4 Pro（深度）"},
        ],
    },
    {
        "provider": "claude",
        "label": "Claude",
        "models": [
            {"key": "claude", "label": "Claude 3.5 Sonnet"},
        ],
    },
]


def get_ai_client(model: str, api_keys: dict) -> AsyncOpenAI:
    """从用户配置中获取 AI 客户端"""
    config = MODEL_CONFIGS.get(model)
    if not config:
        raise ValueError(f"不支持的模型: {model}。可选: {', '.join(MODEL_CONFIGS.keys())}")

    api_key = api_keys.get(config["default_key_label"], "")
    if not api_key:
        raise ValueError(f"请先在设置中配置 {config['name']} 的 API Key")

    return AsyncOpenAI(
        api_key=api_key,
        base_url=config["base_url"],
    )


# ============================================================
# AI 分析报告
# ============================================================
async def generate_analysis_report(
    fund_code: str,
    fund_name: str,
    model: str,
    api_keys: dict,
    portfolio_info: list[dict],
    include_sentiment: bool = True,
    include_technical: bool = True,
) -> dict:
    """
    生成持仓综合分析报告
    - 持仓总体健康度
    - 行业配置建议
    - 风险提示
    - 操作建议
    """
    # 1. 获取技术面数据
    nav_history = await fetch_nav_history(fund_code, days=90)
    tech = predict_trend(nav_history) if nav_history else {"predictions": []}

    # 2. 获取当前估值
    est = await fetch_fund_estimate(fund_code)
    fund_detail = await fetch_fund_detail(fund_code)

    # 3. 构建 AI 提示词
    est_text = ""
    if est:
        est_text = f"""
- 当前单位净值: {est.get('nav', 'N/A')}
- 今日估算净值: {est.get('estimated_nav', 'N/A')}
- 今日估算涨跌: {est.get('estimate_change_pct', 'N/A')}%
- 净值日期: {est.get('nav_date', 'N/A')}"""

    tech_text = ""
    if tech.get("technical_indicators"):
        ti = tech["technical_indicators"]
        tech_text = f"""
- 5日动量: {ti['momentum_5d']}%
- 年化波动率: {ti['volatility_annual']}%
- 夏普比率: {ti['sharpe_ratio']}
- 最大回撤: {ti['max_drawdown']}%
- 历史胜率: {ti['win_rate']}%
- 预期年化收益: {ti['expected_annual_return']}%"""

    portfolio_text = ""
    if portfolio_info:
        portfolio_text = "用户持仓情况:\n"
        for p in portfolio_info[:10]:
            portfolio_text += f"- {p.get('fund_name','')}({p.get('fund_code','')}): 持仓{p.get('shares',0)}份，成本¥{p.get('total_cost',0)}，当前市值¥{p.get('market_value',0)}，盈亏{p.get('profit_loss_pct',0)}%\n"

    prompt = f"""你是一位专业的基金分析师。请基于以下信息，对基金 {fund_name}({fund_code}) 进行综合分析。

## 基金基本信息
- 类型: {fund_detail.get('type', '未知') if fund_detail else '未知'}
- 管理人: {fund_detail.get('manager', '未知') if fund_detail else '未知'}
- 基金公司: {fund_detail.get('company', '未知') if fund_detail else '未知'}
- 风险等级: {fund_detail.get('risk_level', '未知') if fund_detail else '未知'}
{est_text}
{tech_text}
{portfolio_text}

## 分析要求
请从以下维度进行分析，用中文回答，控制在 500 字以内：

1. **市场情绪分析**（{include_sentiment}）：结合当前走势判断市场对该基金的情绪
2. **技术面评估**（{include_technical}）：基于动量/波动率/回撤判断短期趋势
3. **风险提示**：当前持仓需要注意的风险
4. **操作建议**：持有/加仓/减仓 建议及理由

请以 JSON 格式返回：
```json
{{
  "overall_assessment": "综合评估文字",
  "market_sentiment": "市场情绪分析文字",
  "risk_warning": "风险提示文字",
  "advice": "操作建议文字"
}}
```"""

    # 4. 调用 AI
    try:
        client = get_ai_client(model, api_keys)
        config = MODEL_CONFIGS[model]
        response = await client.chat.completions.create(
            model=config["model_id"],
            messages=[
                {"role": "system", "content": "你是一位专业的基金分析师，请始终以简洁准确的中文回复，并以 JSON 格式输出。"},
                {"role": "user", "content": prompt},
            ],
            temperature=0.7,
            max_tokens=2000,
        )
        content = response.choices[0].message.content
        # 尝试解析 JSON
        json_match = content.strip()
        if "```json" in json_match:
            json_match = json_match.split("```json")[1].split("```")[0].strip()
        elif "```" in json_match:
            json_match = json_match.split("```")[1].split("```")[0].strip()
        ai_result = json.loads(json_match)
    except (json.JSONDecodeError, Exception) as e:
        # AI 返回解析失败，使用本地技术分析结果
        ai_result = {
            "overall_assessment": f"基于技术指标分析，{fund_name}近期表现{'稳健' if tech.get('technical_indicators',{}).get('win_rate',50) > 50 else '波动较大'}。",
            "market_sentiment": f"5日动量{tech.get('technical_indicators',{}).get('momentum_5d',0):+.1f}%，短期{'偏多' if tech.get('technical_indicators',{}).get('momentum_5d',0) > 0 else '偏空'}。",
            "risk_warning": f"年化波动率{tech.get('technical_indicators',{}).get('volatility_annual',0):.1f}%，最大回撤{tech.get('technical_indicators',{}).get('max_drawdown',0):.1f}%。",
            "advice": f"建议关注波动率变化，{'可考虑分批建仓' if tech.get('technical_indicators',{}).get('sharpe_ratio',0) > 0.5 else '建议观望等待更好时机'}。",
            "_fallback": True,
        }

    # 5. 合并技术预测
    predictions = tech.get("predictions", [])
    technical_indicators = tech.get("technical_indicators", {})

    return {
        "fund_code": fund_code,
        "fund_name": fund_name,
        "model_used": MODEL_CONFIGS[model]["name"],
        "overall_assessment": ai_result.get("overall_assessment", ""),
        "market_sentiment": ai_result.get("market_sentiment", ""),
        "risk_warning": ai_result.get("risk_warning", ""),
        "advice": ai_result.get("advice", ""),
        "predictions": predictions,
        "technical_indicators": technical_indicators,
        "is_ai_fallback": ai_result.get("_fallback", False),
    }


# ============================================================
# 历史回测
# ============================================================
async def run_backtest(
    fund_code: str,
    investment_amount: float,
    cost_nav: float,
    start_date: str,
    end_date: str,
) -> dict:
    """运行历史回测"""
    nav_history = await fetch_nav_history(fund_code, days=365)
    if not nav_history:
        return {"error": "无法获取净值历史数据"}
    result = backtest_position(nav_history, investment_amount, cost_nav, start_date, end_date)  # pyright: ignore[reportCallIssue]
    return result
