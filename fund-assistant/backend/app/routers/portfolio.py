"""
持仓管理 API 路由 — 支持自动算净值 + 修改历史
"""
import json
from collections import defaultdict
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc

from app.database import get_db
from app.models.user import User
from app.models.portfolio import Portfolio
from app.models.fund import Fund
from app.models.history import PortfolioHistory
from app.schemas.fund import PortfolioCreate, PortfolioResponse, PortfolioHistoryResponse
from app.utils.auth import get_current_user
from app.services.fund_crawler import fetch_fund_estimate, fetch_fund_detail
from app.services.trade_calc import compute_shares_from_amount

router = APIRouter(prefix="/api/portfolio", tags=["持仓管理"])


def _portfolio_to_dict(p: Portfolio) -> dict:
    return {
        "shares": p.shares, "cost_per_share": p.cost_per_share,
        "total_cost": p.total_cost, "buy_date": p.buy_date,
        "fee": p.fee, "note": p.note,
    }


async def _record_history(db: AsyncSession, portfolio: Portfolio, user_id: int,
                          change_type: str, before_snap: dict, after_snap: dict,
                          changed_fields: list[str], note: str = ""):
    """记录修改历史"""
    history = PortfolioHistory(
        portfolio_id=portfolio.id,
        user_id=user_id,
        fund_code=portfolio.fund_code,
        change_type=change_type,
        before_snapshot=before_snap,
        after_snapshot=after_snap,
        change_fields=changed_fields,
        note=note,
    )
    db.add(history)


async def _ensure_fund_exists(db: AsyncSession, fund_code: str) -> Fund | None:
    """确保基金信息在本地数据库存在"""
    result = await db.execute(select(Fund).where(Fund.code == fund_code))
    fund = result.scalar_one_or_none()
    if not fund:
        est = await fetch_fund_estimate(fund_code)
        detail = await fetch_fund_detail(fund_code) if not est else None
        fund = Fund(
            code=fund_code,
            name=est.get("name", "") if est else (detail.get("name", "") if detail else ""),
            type=detail.get("type", "未知") if detail else "未知",
            nav=est.get("nav", 0) if est else 0,
            estimated_nav=est.get("estimated_nav", 0) if est else 0,
            estimate_change_pct=est.get("estimate_change_pct", 0) if est else 0,
            nav_date=est.get("nav_date", "") if est else "",
        )
        db.add(fund)
        await db.flush()
    return fund


def _enrich_portfolio(p: Portfolio, fund: Fund | None) -> dict:
    """补全基金信息 + 计算盈亏"""
    estimated_nav = fund.estimated_nav if fund else 0.0
    current_nav = fund.nav if fund else 0.0
    fund_name = fund.name if fund else ""
    fund_type = fund.type if fund else ""

    market_value = p.shares * (estimated_nav or current_nav)
    profit_loss = market_value - p.total_cost if p.total_cost > 0 else 0
    profit_loss_pct = (profit_loss / p.total_cost * 100) if p.total_cost > 0 else 0.0

    return {
        "id": p.id, "fund_code": p.fund_code, "fund_name": fund_name,
        "fund_type": fund_type, "shares": p.shares, "cost_per_share": p.cost_per_share,
        "total_cost": p.total_cost, "buy_date": p.buy_date, "fee": p.fee,
        "note": p.note or "", "current_nav": current_nav,
        "estimated_nav": estimated_nav, "market_value": round(market_value, 2),
        "profit_loss": round(profit_loss, 2), "profit_loss_pct": round(profit_loss_pct, 2),
    }


@router.get("", response_model=list[PortfolioResponse])
async def list_portfolios(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Portfolio).where(Portfolio.user_id == current_user.id).order_by(Portfolio.created_at.desc())
    )
    portfolios = result.scalars().all()

    enriched = []
    for p in portfolios:
        f_result = await db.execute(select(Fund).where(Fund.code == p.fund_code))
        fund = f_result.scalar_one_or_none()
        if not fund or fund.estimated_nav == 0:
            est = await fetch_fund_estimate(p.fund_code)
            if est and fund:
                fund.estimated_nav = est.get("estimated_nav", 0)
                fund.nav = est.get("nav", 0)
        enriched.append(_enrich_portfolio(p, fund))

    if any(fund and fund.estimated_nav > 0 for _, fund in [(p, None) for p in portfolios]):
        await db.commit()

    return enriched


@router.post("", response_model=PortfolioResponse)
async def create_portfolio(
    data: PortfolioCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """添加持仓 — 支持投资金额 / 原本持有两种模式"""
    shares = data.shares
    cost_per_share = data.cost_per_share
    nav_date = data.buy_date

    # 模式1：新买入 → 只需投资金额，自动算份额
    if data.investment_amount > 0:
        calc = await compute_shares_from_amount(data.fund_code, data.investment_amount, data.buy_time)
        if "error" in calc:
            raise HTTPException(status_code=400, detail=calc["error"])
        shares = calc["shares"]
        cost_per_share = calc["nav"]
        if not nav_date:
            nav_date = calc["nav_date"]

    # 模式2：原本持有 → 给出当前市值+盈亏，用实时净值算份额
    if data.current_value > 0:
        total_spent = data.current_value - data.current_profit  # 总成本
        if total_spent <= 0:
            raise HTTPException(status_code=400, detail="总成本不能为0或负数，请检查盈亏金额")
        # 用实时净值来算份额，这样展示的市值才和用户看到的一致
        est = await fetch_fund_estimate(data.fund_code)
        live_nav = est.get("estimated_nav", 0) or est.get("nav", 0)
        if live_nav <= 0:
            raise HTTPException(status_code=400, detail=f"无法获取 {data.fund_code} 的实时净值，请稍后再试")
        shares = round(data.current_value / live_nav, 2)
        cost_per_share = round(total_spent / shares, 4)
        if not nav_date:
            nav_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    if shares <= 0:
        raise HTTPException(status_code=400, detail="份额不能为0")
    if not nav_date:
        nav_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    total_cost = round(shares * cost_per_share, 2)

    portfolio = Portfolio(
        user_id=current_user.id, fund_code=data.fund_code,
        shares=shares, cost_per_share=round(cost_per_share, 4),
        total_cost=total_cost, buy_date=nav_date,
        fee=data.fee, note=data.note,
    )
    db.add(portfolio)
    await db.flush()

    # 保证基金存在
    fund = await _ensure_fund_exists(db, data.fund_code)
    await _record_history(db, portfolio, current_user.id, "create", {},
                          _portfolio_to_dict(portfolio),
                          ["shares", "cost_per_share", "total_cost"],
                          f"新建持仓：投入¥{total_cost}，自动计算 {shares} 份")

    await db.commit()
    await db.refresh(portfolio)

    return _enrich_portfolio(portfolio, fund)


@router.put("/{portfolio_id}", response_model=PortfolioResponse)
async def update_portfolio(
    portfolio_id: int,
    data: PortfolioCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """更新持仓"""
    result = await db.execute(
        select(Portfolio).where(Portfolio.id == portfolio_id, Portfolio.user_id == current_user.id)
    )
    portfolio = result.scalar_one_or_none()
    if not portfolio:
        raise HTTPException(status_code=404, detail="持仓记录不存在")

    before_snap = _portfolio_to_dict(portfolio)

    shares = data.shares
    cost_per_share = data.cost_per_share

    if data.investment_amount > 0:
        calc = await compute_shares_from_amount(data.fund_code, data.investment_amount, data.buy_time)
        if "error" in calc:
            raise HTTPException(status_code=400, detail=calc["error"])
        shares = calc["shares"]
        cost_per_share = calc["nav"]

    # 支持原本持有模式更新
    if data.current_value > 0:
        total_spent = data.current_value - data.current_profit
        if total_spent <= 0:
            raise HTTPException(status_code=400, detail="总成本不能为0或负数")
        est = await fetch_fund_estimate(data.fund_code)
        live_nav = est.get("estimated_nav", 0) or est.get("nav", 0)
        if live_nav <= 0:
            raise HTTPException(status_code=400, detail=f"无法获取实时净值")
        shares = round(data.current_value / live_nav, 2)
        cost_per_share = round(total_spent / shares, 4)

    if shares > 0 and cost_per_share > 0:
        portfolio.shares = shares
        portfolio.cost_per_share = round(cost_per_share, 4)
        portfolio.total_cost = round(shares * cost_per_share, 2)
    if data.buy_date:
        portfolio.buy_date = data.buy_date
    portfolio.fee = data.fee
    portfolio.note = data.note

    await db.flush()
    after_snap = _portfolio_to_dict(portfolio)

    changed = [k for k in before_snap if before_snap.get(k) != after_snap.get(k)]
    await _record_history(db, portfolio, current_user.id, "update", before_snap, after_snap,
                          changed, f"修改持仓")

    await db.commit()
    await db.refresh(portfolio)

    f_result = await db.execute(select(Fund).where(Fund.code == portfolio.fund_code))
    fund = f_result.scalar_one_or_none()
    return _enrich_portfolio(portfolio, fund)


@router.delete("/{portfolio_id}")
async def delete_portfolio(
    portfolio_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Portfolio).where(Portfolio.id == portfolio_id, Portfolio.user_id == current_user.id)
    )
    portfolio = result.scalar_one_or_none()
    if not portfolio:
        raise HTTPException(status_code=404, detail="持仓记录不存在")

    before_snap = _portfolio_to_dict(portfolio)
    await _record_history(db, portfolio, current_user.id, "delete", before_snap, {},
                          ["shares", "cost_per_share", "total_cost"],
                          "删除持仓")

    await db.delete(portfolio)
    await db.commit()
    return {"message": "删除成功"}


@router.get("/analysis")
async def get_portfolio_analysis(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    days: int = 365,
):
    """
    收益历史分析：日/月/年 维度 + 胜率 + 分布
    """
    from collections import defaultdict
    import math

    result = await db.execute(
        select(Portfolio).where(Portfolio.user_id == current_user.id)
    )
    portfolios = result.scalars().all()
    if not portfolios:
        return {"daily": [], "monthly": [], "yearly": [], "win_rate": 0, "total_pl": 0}

    # 收集每笔持仓：份额 + 买入日期 + 成本
    per_position: list[dict] = []
    total_invested = 0.0
    for p in portfolios:
        per_position.append({
            "code": p.fund_code,
            "shares": p.shares,
            "buy_date": p.buy_date,
            "total_cost": p.total_cost,
        })
        total_invested += p.total_cost

    # 获取所有基金的净值历史
    from app.services.fund_crawler import fetch_nav_history, fetch_fund_estimate

    codes = list(set(p["code"] for p in per_position))
    nav_data: dict[str, list[dict]] = {}
    for code in codes:
        history = await fetch_nav_history(code, days=max(days, 365))
        if history:
            nav_data[code] = history

    if not nav_data:
        return {"daily": [], "monthly": [], "yearly": [], "win_rate": 0, "total_pl": 0, "start_date": ""}

    # 按日期汇总 — 每笔持仓只从买入日算起
    date_values: dict[str, float] = defaultdict(float)
    date_changes: dict[str, float] = defaultdict(float)
    all_dates = set()

    for pos in per_position:
        code = pos["code"]
        shares = pos["shares"]
        buy_date = pos["buy_date"]
        history = nav_data.get(code, [])
        if not history or shares <= 0:
            continue
        prev_nav = None
        for h in history:
            d = h["date"]
            if d < buy_date:
                continue  # 买入前的数据跳过
            all_dates.add(d)
            nav = h["nav"]
            val = shares * nav
            date_values[d] += val
            if prev_nav is not None:
                date_changes[d] += shares * (nav - prev_nav)
            prev_nav = nav

    sorted_dates = sorted(all_dates)
    if not sorted_dates:
        return {"daily": [], "monthly": [], "yearly": [], "win_rate": 0, "total_pl": 0}

    # 日维度 + 累计收益曲线
    daily = []
    curve = []  # 累计收益折线数据
    gains = []
    losses = []
    for d in sorted_dates:
        total_val = round(date_values[d], 2)
        profit = round(total_val - total_invested, 2)
        change = round(date_changes.get(d, 0), 2)
        daily.append({"date": d, "value": total_val, "profit": profit, "change": change})
        curve.append({"date": d, "profit": profit})
        if change > 0:
            gains.append(change)
        elif change < 0:
            losses.append(abs(change))

    # 周维度（按 ISO 周）
    from datetime import date as dt_date
    weekly_map: dict[str, dict] = {}
    for d in daily:
        y, w, _ = dt_date.fromisoformat(d["date"]).isocalendar()
        wk = f"{y}-W{w:02d}"
        if wk not in weekly_map:
            weekly_map[wk] = {"week": wk, "profit": 0, "change": 0}
        weekly_map[wk]["profit"] = d["profit"]
        weekly_map[wk]["change"] = round(weekly_map[wk]["change"] + d["change"], 2)
    weekly = sorted(weekly_map.values(), key=lambda x: x["week"])

    # 月维度
    monthly_map: dict[str, dict] = {}
    for d in daily:
        month_key = d["date"][:7]  # YYYY-MM
        if month_key not in monthly_map:
            monthly_map[month_key] = {"month": month_key, "value": 0, "change": 0, "days": 0}
        monthly_map[month_key]["value"] = d["value"]
        monthly_map[month_key]["change"] = round(monthly_map[month_key]["change"] + d["change"], 2)
        monthly_map[month_key]["days"] += 1
    monthly = sorted(monthly_map.values(), key=lambda x: x["month"])

    # 年维度
    yearly_map: dict[str, dict] = {}
    for m in monthly:
        year_key = m["month"][:4]
        if year_key not in yearly_map:
            yearly_map[year_key] = {"year": year_key, "value": 0, "change": 0}
        yearly_map[year_key]["value"] = m["value"]
        yearly_map[year_key]["change"] = round(yearly_map[year_key]["change"] + m["change"], 2)
    yearly = sorted(yearly_map.values(), key=lambda x: x["year"])

    # 胜率：上涨天数 / 总交易天数
    up_days = sum(1 for d in daily if d["change"] > 0)
    flat_days = sum(1 for d in daily if d["change"] == 0)
    total_trading_days = len([d for d in daily if d["change"] != 0])
    win_rate = round(up_days / total_trading_days * 100, 1) if total_trading_days > 0 else 0

    # 总盈亏
    current_total = round(sum(date_values.get(d, 0) for d in [sorted_dates[-1]] if sorted_dates), 2) if sorted_dates else total_invested
    total_pl = round(current_total - total_invested, 2)

    # 盈利分布（用于图表）
    distribution = {
        "up_days": up_days,
        "down_days": len([d for d in daily if d["change"] < 0]),
        "flat_days": flat_days,
        "best_day": max(gains) if gains else 0,
        "worst_day": -max(losses) if losses else 0,
        "avg_gain": round(sum(gains) / len(gains), 2) if gains else 0,
        "avg_loss": round(sum(losses) / len(losses), 2) if losses else 0,
        "max_win_streak": 0,  # TODO
    }

    earliest_buy = min(p["buy_date"] for p in per_position if p["buy_date"]) if per_position else ""

    # 沪深300 基准对比
    benchmark = await _fetch_hs300_benchmark(sorted_dates[0] if sorted_dates else "", days)

    return {
        "daily": daily[-90:],
        "weekly": weekly[-52:],
        "monthly": monthly[-24:],
        "yearly": yearly,
        "curve": curve,
        "benchmark": benchmark,
        "win_rate": win_rate,
        "total_pl": total_pl,
        "distribution": distribution,
        "total_invested": round(total_invested, 2),
        "current_value": current_total,
        "start_date": earliest_buy,
    }


async def _fetch_hs300_benchmark(start_date: str, days: int) -> list[dict]:
    """获取沪深300历史数据作为基准"""
    if not start_date:
        return []
    try:
        import httpx
        url = "https://push2his.eastmoney.com/api/qt/stock/kline/get"
        params = {
            "secid": "1.000300",
            "fields1": "f1,f2,f3,f4,f5,f6",
            "fields2": "f51,f52,f53,f54,f55,f56,f57,f58",
            "klt": "101",
            "fqt": "0",
            "lmt": str(max(days, 60)),
            "_": str(int(__import__('time').time() * 1000)),
        }
        async with httpx.AsyncClient(timeout=10) as c:
            r = await c.get(url, params=params)
            data = r.json()
        klines = data.get("data", {}).get("klines", [])
        if not klines:
            return []

        # 找到起始日期的点位作为基准
        base_point = None
        result = []
        for line in klines:
            parts = line.split(",")
            d = parts[0]  # 日期
            close = float(parts[2])  # 收盘价
            if d < start_date:
                continue
            if base_point is None:
                base_point = close
            if base_point and base_point > 0:
                pct = round((close - base_point) / base_point * 100, 2)
                result.append({"date": d, "pct": pct})
        return result
    except Exception:
        return []


@router.post("/batch")
async def batch_create(
    funds: list[dict],
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """批量导入持仓"""
    results = []
    for item in funds:
        code = item.get("fund_code", "")
        name = item.get("fund_name", "")
        current_value = float(item.get("current_value", 0))
        current_profit = float(item.get("current_profit", 0))

        if current_value <= 0:
            continue

        total_spent = current_value - current_profit
        if total_spent <= 0:
            continue

        # 获取实时净值
        if code:
            est = await fetch_fund_estimate(code)
        else:
            est = None

        live_nav = est.get("estimated_nav", 0) or est.get("nav", 0) if est else 0
        if live_nav <= 0:
            live_nav = 1.0  # fallback

        shares = round(current_value / live_nav, 2)
        cost_per_share = round(total_spent / shares, 4)
        nav_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")

        # 如果有代码，确保基金存在
        if code:
            await _ensure_fund_exists(db, code)

        portfolio = Portfolio(
            user_id=current_user.id,
            fund_code=code or name[:10],
            shares=shares,
            cost_per_share=cost_per_share,
            total_cost=round(shares * cost_per_share, 2),
            buy_date=nav_date,
            note=f"同步导入: {name}",
        )
        db.add(portfolio)
        await db.flush()
        await _record_history(db, portfolio, current_user.id, "create", {},
                              _portfolio_to_dict(portfolio),
                              ["shares", "cost_per_share", "total_cost"],
                              f"批量同步: {name} 市值¥{current_value}")

        results.append({"name": name, "code": code, "status": "ok"})

    await db.commit()
    return {"imported": len(results), "funds": results}


@router.get("/{portfolio_id}/history", response_model=list[PortfolioHistoryResponse])
async def get_portfolio_history(
    portfolio_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """查看某条持仓的修改历史"""
    result = await db.execute(
        select(PortfolioHistory)
        .where(PortfolioHistory.portfolio_id == portfolio_id,
               PortfolioHistory.user_id == current_user.id)
        .order_by(desc(PortfolioHistory.created_at))
        .limit(50)
    )
    histories = result.scalars().all()
    return [{
        "id": h.id, "portfolio_id": h.portfolio_id, "fund_code": h.fund_code,
        "change_type": h.change_type, "change_fields": h.change_fields or [],
        "before_snapshot": h.before_snapshot or {}, "after_snapshot": h.after_snapshot or {},
        "note": h.note or "", "created_at": h.created_at.isoformat() if h.created_at else "",
    } for h in histories]
