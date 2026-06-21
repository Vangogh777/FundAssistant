"""
交易时间 / 净值自动计算
- 判断交易日（周一至周五，排除中国大陆节假日）
- 下午3点前 → 当天净值，3点后 → 下一交易日净值
- 根据买入金额自动算份额
"""
import datetime as _dt
from app.services.fund_crawler import fetch_nav_history, fetch_fund_estimate

# 2025-2026 中国大陆法定节假日（简化版，以官方为准）
CN_HOLIDAYS_2025_2026 = {
    "2025-01-01", "2025-01-28", "2025-01-29", "2025-01-30", "2025-01-31",
    "2025-02-01", "2025-02-02", "2025-02-03", "2025-02-04",
    "2025-04-04", "2025-04-05", "2025-04-06",
    "2025-05-01", "2025-05-02", "2025-05-03", "2025-05-04", "2025-05-05",
    "2025-05-31", "2025-06-01", "2025-06-02",
    "2025-10-01", "2025-10-02", "2025-10-03", "2025-10-04", "2025-10-05", "2025-10-06", "2025-10-07", "2025-10-08",
    "2026-01-01", "2026-01-02",
    "2026-02-16", "2026-02-17", "2026-02-18", "2026-02-19", "2026-02-20", "2026-02-21", "2026-02-22",
    "2026-04-03", "2026-04-04", "2026-04-05",
    "2026-05-01", "2026-05-02", "2026-05-03", "2026-05-04",
    "2026-06-19", "2026-06-20", "2026-06-21",
    "2026-10-01", "2026-10-02", "2026-10-03", "2026-10-04", "2026-10-05", "2026-10-06", "2026-10-07",
}

# 特殊调休工作日（周末但上班）
CN_WORK_WEEKENDS = {
    "2025-01-26", "2025-02-08",
    "2025-04-27", "2025-09-28", "2025-10-11",
    "2026-02-14", "2026-02-28",
    "2026-09-27", "2026-10-10",
}


def is_trading_day(date_str: str) -> bool:
    """判断是否为 A 股交易日"""
    d = _dt.date.fromisoformat(date_str)
    if d.strftime("%Y-%m-%d") in CN_WORK_WEEKENDS:
        return True
    if d.weekday() >= 5:  # 周六周日
        return False
    if d.strftime("%Y-%m-%d") in CN_HOLIDAYS_2025_2026:
        return False
    return True


def get_next_trading_day(date_str: str) -> str:
    """获取下一个交易日"""
    d = _dt.date.fromisoformat(date_str)
    for _ in range(10):
        d += _dt.timedelta(days=1)
        if is_trading_day(d.isoformat()):
            return d.isoformat()
    return d.isoformat()


def get_effective_nav_date(buy_datetime: str | None = None) -> str:
    """
    根据买入时间确定净值日期
    - 下午3点前 → 当天（如果是交易日）
    - 下午3点后 → 下一个交易日
    - 非交易日 → 下一个交易日
    返回: 净值日期 "YYYY-MM-DD"
    """
    if buy_datetime:
        try:
            dt = _dt.datetime.fromisoformat(buy_datetime)
        except (ValueError, TypeError):
            dt = _dt.datetime.now()
    else:
        dt = _dt.datetime.now()

    day_str = dt.strftime("%Y-%m-%d")
    hour = dt.hour
    minute = dt.minute

    # 午3点 cutoff
    if hour < 15 or (hour == 15 and minute == 0):
        # 当天
        if is_trading_day(day_str):
            return day_str
        else:
            return get_next_trading_day(day_str)
    else:
        # 下一个交易日
        return get_next_trading_day(day_str)


async def compute_shares_from_amount(
    fund_code: str,
    investment_amount: float,
    buy_datetime: str | None = None,
) -> dict:
    """
    根据投入金额自动计算份额
    Returns: {"shares": float, "nav": float, "nav_date": str, "effective_date": str}
    """
    nav_date = get_effective_nav_date(buy_datetime)

    # 尝试获取指定日期的净值
    history = await fetch_nav_history(fund_code, days=30)
    nav = None
    for h in history:
        if h["date"] == nav_date:
            nav = h["nav"]
            break

    if not nav or nav <= 0:
        # 回退到最新估值
        est = await fetch_fund_estimate(fund_code)
        if est and est.get("nav", 0) > 0:
            nav = est["nav"]
            nav_date = est.get("nav_date", nav_date)

    if not nav or nav <= 0:
        return {"error": "无法获取基金净值"}

    shares = investment_amount / nav
    return {
        "shares": round(shares, 2),
        "nav": nav,
        "nav_date": nav_date,
        "effective_date": nav_date,
        "investment_amount": investment_amount,
        "fee": 0.0,
    }
