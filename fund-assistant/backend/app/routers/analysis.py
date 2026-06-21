"""
AI 分析 + 回测 API 路由
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.models.user import User
from app.models.portfolio import Portfolio
from app.models.fund import Fund
from app.schemas.analysis import AIAnalysisRequest, AIAnalysisResponse
from app.services.ai_analyzer import generate_analysis_report, run_backtest, MODEL_PROVIDERS
from app.services.valuation import predict_trend
from app.services.fund_crawler import fetch_fund_estimate, fetch_nav_history, fetch_fund_detail
from app.services.holdings_analysis import fetch_fund_holdings, fetch_fund_sector_allocation, fetch_stock_brief
from app.utils.auth import get_current_user

router = APIRouter(prefix="/api/analysis", tags=["AI分析"])


@router.get("/models")
async def list_models():
    """获取可用的 AI 模型列表"""
    return MODEL_PROVIDERS


@router.post("/ai", response_model=AIAnalysisResponse)
async def analyze_fund(
    data: AIAnalysisRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """AI 综合分析（含持仓分析+预测+回测）"""
    # 获取基金信息
    est = await fetch_fund_estimate(data.fund_code)
    if not est:
        raise HTTPException(status_code=404, detail="未找到该基金")

    fund_name = est.get("name", data.fund_code)

    # 获取用户该基金持仓
    result = await db.execute(
        select(Portfolio).where(Portfolio.user_id == current_user.id, Portfolio.fund_code == data.fund_code)
    )
    user_portfolios = result.scalars().all()

    # 构建持仓信息
    portfolio_info = []
    for p in user_portfolios:
        portfolio_info.append({
            "fund_name": fund_name,
            "fund_code": p.fund_code,
            "shares": p.shares,
            "total_cost": p.total_cost,
            "cost_per_share": p.cost_per_share,
            "buy_date": p.buy_date,
            "market_value": round(p.shares * est.get("estimated_nav", est.get("nav", 0)), 2),
            "profit_loss_pct": round((est.get("estimated_nav", 0) - p.cost_per_share) / p.cost_per_share * 100, 2) if p.cost_per_share > 0 else 0,
        })

    # 生成 AI 分析报告
    result_data = await generate_analysis_report(
        fund_code=data.fund_code,
        fund_name=fund_name,
        model=data.model,
        api_keys=current_user.api_keys or {},
        portfolio_info=portfolio_info,
        include_sentiment=data.include_sentiment,
        include_technical=data.include_technical,
    )

    # 回测（如果有持仓）
    backtest = None
    if portfolio_info:
        p = portfolio_info[0]
        nav_history = await fetch_nav_history(data.fund_code, days=365)
        if nav_history and len(nav_history) > 30:
            from app.services.valuation import backtest_position
            start = min(r["date"] for r in nav_history)
            end = max(r["date"] for r in nav_history)
            bt = backtest_position(nav_history, p["total_cost"], p["cost_per_share"], start, end)
            if "error" not in bt:
                bt["fund_code"] = data.fund_code
                bt["fund_name"] = fund_name
                backtest = bt

    return {
        **result_data,
        "backtest": backtest,
    }


@router.get("/predict/{fund_code}")
async def predict_trend_simple(fund_code: str, days: int = 90):
    """快捷预测（仅技术面，无需 AI Key）"""
    nav_history = await fetch_nav_history(fund_code, days=days)
    if not nav_history:
        raise HTTPException(status_code=404, detail="无法获取净值历史")

    result = predict_trend(nav_history)
    est = await fetch_fund_estimate(fund_code)
    return {
        "fund_code": fund_code,
        "fund_name": est.get("name", "") if est else "",
        "predictions": result.get("predictions", []),
        "technical_indicators": result.get("technical_indicators", {}),
    }


@router.get("/portfolio-report")
async def get_portfolio_report(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    持仓基金综合分析：穿透持仓 + 行业分布 + AI建议
    """
    result = await db.execute(
        select(Portfolio).where(Portfolio.user_id == current_user.id)
    )
    portfolios = result.scalars().all()
    if not portfolios:
        return {"error": "暂无持仓"}

    funds_analysis = []
    all_stocks: dict[str, dict] = {}
    sector_map: dict[str, float] = {}

    for p in portfolios:
        # 获取基金信息
        f_result = await db.execute(select(Fund).where(Fund.code == p.fund_code))
        fund = f_result.scalar_one_or_none()

        fund_name = fund.name if fund else p.fund_code
        fund_type = fund.type if fund else "未知"

        # 穿透持仓
        holdings = await fetch_fund_holdings(p.fund_code)

        # 行业配置
        sector = await fetch_fund_sector_allocation(p.fund_code)

        # 汇总行业
        if sector.get("allocation"):
            for asset_type, ratio in sector["allocation"].items():
                sector_map[asset_type] = sector_map.get(asset_type, 0) + ratio * (p.total_cost or 1)

        # 汇总重仓股
        for stock in holdings.get("top_holdings", []):
            s_code = stock["code"]
            if s_code not in all_stocks:
                all_stocks[s_code] = {**stock, "funds": [], "total_weight": 0}
            all_stocks[s_code]["funds"].append({
                "fund_name": fund_name,
                "fund_code": p.fund_code,
                "weight_in_fund": stock["ratio"],
            })
            all_stocks[s_code]["total_weight"] += stock["ratio"] * (p.total_cost or 1)

        # 计算持仓占比
        est = await fetch_fund_estimate(p.fund_code)
        current_nav = est.get("estimated_nav", fund.nav if fund else 0)
        market_value = p.shares * current_nav if current_nav > 0 else p.total_cost
        profit_pct = ((current_nav - p.cost_per_share) / p.cost_per_share * 100) if p.cost_per_share > 0 else 0

        funds_analysis.append({
            "fund_code": p.fund_code,
            "fund_name": fund_name,
            "fund_type": fund_type,
            "shares": p.shares,
            "total_cost": p.total_cost,
            "market_value": round(market_value, 2),
            "profit_loss": round(market_value - p.total_cost, 2),
            "profit_pct": round(profit_pct, 2),
            "holdings_count": len(holdings.get("top_holdings", [])),
            "sector": sector.get("allocation", {}),
            "top_holdings": holdings.get("top_holdings", [])[:5],
        })

    # 按权重排序重仓股
    sorted_stocks = sorted(all_stocks.values(), key=lambda x: x["total_weight"], reverse=True)
    top_stocks = sorted_stocks[:15]

    # 获取重仓股实时行情
    import asyncio
    stock_quotes = await asyncio.gather(*[
        fetch_stock_brief(s["code"]) for s in top_stocks
    ], return_exceptions=True)

    for i, s in enumerate(top_stocks):
        if isinstance(stock_quotes[i], dict):
            s.update(stock_quotes[i])

    # 生成 AI 提示
    report_prompt = _build_portfolio_report_prompt(funds_analysis, top_stocks, sector_map)

    return {
        "funds": funds_analysis,
        "top_stocks": top_stocks[:10],
        "sector_allocation": sector_map,
        "ai_prompt": report_prompt,
    }


def _build_portfolio_report_prompt(funds: list, stocks: list, sectors: dict) -> str:
    funds_text = ""
    for f in funds:
        funds_text += f"- {f['fund_name']}({f['fund_code']}) | {f['fund_type']} | 市值¥{f['market_value']} | 盈亏{f['profit_pct']:+.1f}%\n"

    stocks_text = ""
    for s in stocks[:10]:
        chg = s.get('change_pct', 0) or 0
        stocks_text += f"- {s.get('name','')}({s.get('code','')}) | ¥{s.get('price',0)} | {chg:+.1f}% | 权重{s.get('total_weight',0):.2f}\n"

    return f"""请分析用户的基金持仓组合，给出交易建议。

## 用户持仓
{funds_text}

## 穿透重仓股
{stocks_text}

## 行业配置
{sectors}

请按以下固定格式回复：

【组合总评】
（一段话概括整体情况，50字内）

【风险等级】
高/中/低风险，理由一句话

【加仓建议】
- 基金名称(代码)：建议（如：可加仓/暂不加仓），理由

【减仓/清仓建议】  
- 基金名称(代码)：建议（如：减仓/清仓/继续持有），理由

【补仓建议】
- 基金名称(代码)：建议（如：可补仓/不建议），理由

【后市展望】
（一段话，50字内）

请用 JSON 格式返回：{{"overall":"","risk":"","add_positions":[],"reduce_positions":[],"add_more":[],"outlook":""}}"""


@router.get("/backtest/{fund_code}")
async def backtest_fund(
    fund_code: str,
    investment_amount: float = 10000.0,
    cost_nav: float = 1.0,
    start_date: str = "2025-01-01",
    end_date: str = "2026-01-01",
    current_user: User = Depends(get_current_user),
):
    """历史回测"""
    return await run_backtest(fund_code, investment_amount, cost_nav, start_date, end_date)
