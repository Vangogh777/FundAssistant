"""
基金估值 + 市场技术分析服务
- 多数据源均衡估值（加权平均）
- 1-7天涨跌预测（5日动量/波动率/预期收益/上涨概率）
- 大盘资金流向分析
- 历史回测计算
"""
import math
from datetime import datetime, timedelta
from typing import Optional


# ============================================================
# 多数据源均衡估值
# ============================================================
def compute_weighted_valuation(sources: dict[str, float], weights: Optional[dict[str, float]] = None) -> dict:
    """
    从多个数据源计算加权平均估值
    sources: {"eastmoney": 1.234, "fundsite": 1.235, ...}
    weights: {"eastmoney": 0.5, "fundsite": 0.5, ...}
    默认权重均分
    """
    if not sources:
        return {"weighted_nav": 0.0, "sources": {}, "confidence": 0}

    if not weights:
        w = 1.0 / len(sources)
        weights = {k: w for k in sources}

    weighted = 0.0
    total_w = 0.0
    for src, val in sources.items():
        wt = weights.get(src, 0.0)
        if val and val > 0:
            weighted += val * wt
            total_w += wt

    if total_w == 0:
        return {"weighted_nav": 0.0, "sources": sources, "confidence": 0}

    result = {
        "weighted_nav": round(weighted / total_w, 4),
        "sources": sources,
        "confidence": round(total_w * 100, 1),
    }
    return result


# ============================================================
# 技术分析指标
# ============================================================
def calc_momentum(nav_list: list[float], days: int = 5) -> float:
    """N 日动量（价格变化率 ROC）"""
    if len(nav_list) < days or nav_list[-days] == 0:
        return 0.0
    return round((nav_list[-1] - nav_list[-days]) / nav_list[-days] * 100, 2)


def calc_volatility(returns: list[float]) -> float:
    """年化波动率"""
    n = len(returns)
    if n < 2:
        return 0.0
    mean = sum(returns) / n
    variance = sum((r - mean) ** 2 for r in returns) / (n - 1)
    daily_vol = math.sqrt(variance)
    annual_vol = daily_vol * math.sqrt(250)  # 年化
    return round(annual_vol * 100, 2)  # 转为百分比


def calc_sharpe_ratio(returns: list[float], risk_free: float = 0.03) -> float:
    """夏普比率"""
    if len(returns) < 2:
        return 0.0
    mean = sum(returns) / len(returns)
    annual_return = mean * 250
    vol = calc_volatility(returns) / 100  # 转回小数
    if vol == 0:
        return 0.0
    return round((annual_return - risk_free) / vol, 2)


def calc_max_drawdown(nav_list: list[float]) -> float:
    """最大回撤 %"""
    if len(nav_list) < 2:
        return 0.0
    peak = nav_list[0]
    max_dd = 0.0
    for nav in nav_list:
        if nav > peak:
            peak = nav
        dd = (peak - nav) / peak
        if dd > max_dd:
            max_dd = dd
    return round(max_dd * 100, 2)


def calc_win_rate(returns: list[float]) -> float:
    """胜率（收益为正的天数占比）"""
    if not returns:
        return 0.0
    wins = sum(1 for r in returns if r > 0)
    return round(wins / len(returns) * 100, 1)


# ============================================================
# 1-7 天涨跌预测
# ============================================================
def predict_trend(
    nav_history: list[dict],
    market_sentiment: float = 0.0,
) -> dict:
    """
    基于历史净值、技术指标计算 1-7 天预测
    返回各时间窗口的预测涨跌幅、可信度、关键因素
    """
    if not nav_history or len(nav_history) < 30:
        return {
            "predictions": [],
            "message": "数据不足（需要至少30个交易日的历史净值）",
        }

    # 提取净值序列
    navs = [r["nav"] for r in nav_history if r.get("nav", 0) > 0]
    if len(navs) < 30:
        return {"predictions": [], "message": "有效净值数据不足"}

    # 日收益率
    returns = []
    for i in range(1, len(navs)):
        if navs[i - 1] > 0:
            returns.append((navs[i] - navs[i - 1]) / navs[i - 1])

    if len(returns) < 20:
        return {"predictions": [], "message": "收益率数据不足"}

    # 计算技术指标
    momentum_5d = calc_momentum(navs, 5)
    volatility = calc_volatility(returns)
    sharpe = calc_sharpe_ratio(returns)
    max_dd = calc_max_drawdown(navs)
    win_rate = calc_win_rate(returns)
    avg_return = sum(returns) / len(returns)
    recent_returns = returns[-5:] if len(returns) >= 5 else returns
    recent_avg = sum(recent_returns) / len(recent_returns)

    # 预期年化收益
    annual_return = avg_return * 250 * 100  # %

    # 预测各周期的涨跌
    periods = [1, 3, 5, 7]
    predictions = []

    for days in periods:
        # 基础预测 = 近期平均日收益 * 天数 + 动量修正
        base_pred = recent_avg * days * 100  # 转为 %
        momentum_factor = momentum_5d * 0.3 * (days / 5)
        predicted_pct = round(base_pred + momentum_factor, 2)

        # ---- 可信度：周期越长越不确定 ----
        vol_penalty = volatility / 100
        # 基础可信度随天数递减（1天=75, 7天=57）
        confidence_base = max(20, 75 - vol_penalty * 15 - days * 3)
        # 动量一致性
        momentum_consistent = (predicted_pct > 0 and momentum_5d > 0) or (predicted_pct < 0 and momentum_5d < 0)
        momentum_bonus = 10 if momentum_consistent else -10
        # 夏普比率 + 胜率
        sharpe_bonus = min(10, max(-10, sharpe * 5))
        win_bonus = (win_rate - 50) * 0.2
        confidence = round(max(10, min(95, confidence_base + momentum_bonus + sharpe_bonus + win_bonus)), 1)

        # ---- 上涨概率：长期靠胜率，短期靠趋势 ----
        # 基础 = 历史胜率
        base_prob = win_rate * 0.6 + 20
        # 短期趋势影响（1天权重高，7天权重低）
        short_term_weight = (7 - days) / 7
        trend_boost = (15 if recent_avg > 0 else -15) * short_term_weight
        # 动量影响（累积效应，周期越长动量越重要）
        momentum_impact = momentum_5d * 2 * (days / 5)
        up_prob = round(max(5, min(95, base_prob + trend_boost + momentum_impact)), 1)

        # 关键因素（含周期相关因子）
        factors = []
        if abs(momentum_5d) > 2:
            factors.append(f"5日动量 {momentum_5d:+.1f}%")
        if volatility > 25:
            factors.append(f"波动率 {volatility}% 偏高")
        if max_dd > 15:
            factors.append(f"最大回撤 {max_dd}%")
        if days >= 5 and abs(predicted_pct) > 3:
            direction = "涨" if predicted_pct > 0 else "跌"
            factors.append(f"{days}日趋势偏{direction}")

        predictions.append({
            "period": f"{days}d",
            "predicted_change_pct": predicted_pct,
            "confidence_score": confidence,
            "confidence_reason": f"基于{days}日动量+波动率{volatility}%+胜率{win_rate}%综合评估",
            "key_factors": factors,
            "up_probability": up_prob,
        })

    return {
        "predictions": predictions,
        "technical_indicators": {
            "momentum_5d": momentum_5d,
            "volatility_annual": volatility,
            "sharpe_ratio": sharpe,
            "max_drawdown": max_dd,
            "win_rate": win_rate,
            "expected_annual_return": round(annual_return, 2),
            "avg_daily_return": round(avg_return * 100, 4),
            "recent_avg_daily_return": round(recent_avg * 100, 4),
        },
    }


# ============================================================
# 历史回测
# ============================================================
def backtest_position(
    nav_history: list[dict],
    investment_amount: float,
    cost_nav: float,
    start_date: str,
    end_date: str,
) -> dict:
    """
    回测：假设在 start_date 以 cost_nav 买入 investment_amount，持有到 end_date
    """
    if not nav_history:
        return {"error": "无历史数据"}

    # 找到区间的净值数据
    period_navs = [r for r in nav_history if start_date <= r["date"] <= end_date]
    if len(period_navs) < 2:
        return {"error": f"区间 {start_date} ~ {end_date} 内数据不足"}

    # 计算份额
    shares = investment_amount / cost_nav
    end_nav = period_navs[-1]["nav"]
    final_value = shares * end_nav
    total_return = (final_value - investment_amount) / investment_amount * 100

    # 计算回测期间的指标
    nav_sequence = [r["nav"] for r in period_navs]
    navs_with_init = [cost_nav] + nav_sequence

    period_returns = []
    for i in range(1, len(navs_with_init)):
        if navs_with_init[i - 1] > 0:
            period_returns.append((navs_with_init[i] - navs_with_init[i - 1]) / navs_with_init[i - 1])

    # 年化收益
    days = (datetime.strptime(end_date, "%Y-%m-%d") -
            datetime.strptime(start_date, "%Y-%m-%d")).days
    if days > 0 and period_returns:
        total_r = (final_value / investment_amount) - 1
        annual_return = ((1 + total_r) ** (365 / days) - 1) * 100
    else:
        annual_return = 0.0

    max_dd = calc_max_drawdown(navs_with_init)
    sharpe = calc_sharpe_ratio(period_returns) if period_returns else 0.0
    vol = calc_volatility(period_returns) if period_returns else 0.0
    win_rate = calc_win_rate(period_returns) if period_returns else 0.0

    return {
        "period_start": period_navs[0]["date"],
        "period_end": period_navs[-1]["date"],
        "days": days,
        "initial_investment": investment_amount,
        "shares": round(shares, 2),
        "final_value": round(final_value, 2),
        "total_return_pct": round(total_return, 2),
        "annualized_return_pct": round(annual_return, 2),
        "max_drawdown": max_dd,
        "sharpe_ratio": sharpe,
        "volatility": vol,
        "win_rate": win_rate,
        "end_nav": end_nav,
        "profit_loss": round(final_value - investment_amount, 2),
    }
