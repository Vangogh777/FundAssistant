from pydantic import BaseModel
from typing import Optional


class FundBase(BaseModel):
    code: str
    name: str
    type: Optional[str] = "混合型"
    company: Optional[str] = ""
    manager: Optional[str] = ""


class FundCreate(FundBase):
    pass


class FundResponse(FundBase):
    id: int
    nav: float
    accumulated_nav: float
    estimated_nav: float
    estimate_change_pct: float
    nav_date: str
    risk_level: str
    fund_scale: str
    multi_source_data: dict

    class Config:
        from_attributes = True


class FundSearchResult(BaseModel):
    code: str
    name: str
    type: str
    nav: float
    estimate_change_pct: float


class FundNavResponse(BaseModel):
    date: str
    nav: float
    accumulated_nav: float
    daily_change_pct: float


class PortfolioCreate(BaseModel):
    fund_code: str
    shares: float = 0.0                     # 手动份额（可填0，由investment_amount或current_value自动算）
    cost_per_share: float = 0.0             # 手动成本价（可填0）
    investment_amount: float = 0.0          # 投入金额（填此项则自动算份额+净值）
    current_value: float = 0.0              # 原本持有：当前市值（填此项+current_profit则自动算）
    current_profit: float = 0.0             # 原本持有：当前盈亏
    buy_date: str = ""                      # 买入日期
    buy_time: str | None = None             # 精确买入时间 "2026-01-15T14:30:00"
    fee: float = 0.0
    note: str = ""


class PortfolioHistoryResponse(BaseModel):
    id: int
    portfolio_id: int
    fund_code: str
    change_type: str
    change_fields: list
    before_snapshot: dict
    after_snapshot: dict
    note: str
    created_at: str

    class Config:
        from_attributes = True


class PortfolioResponse(BaseModel):
    id: int
    fund_code: str
    fund_name: str = ""
    fund_type: str = ""
    shares: float
    cost_per_share: float
    total_cost: float
    buy_date: str
    fee: float
    note: str
    current_nav: float = 0.0
    estimated_nav: float = 0.0
    market_value: float = 0.0
    profit_loss: float = 0.0
    profit_loss_pct: float = 0.0

    class Config:
        from_attributes = True


class DripPlanCreate(BaseModel):
    fund_code: str
    amount: float
    frequency: str
    day_of_week: int = 1
    day_of_month: int = 1
    next_run_date: str
    note: str = ""


class DripPlanResponse(BaseModel):
    id: int
    fund_code: str
    fund_name: str = ""
    amount: float
    frequency: str
    day_of_week: int
    day_of_month: int
    next_run_date: str
    is_active: bool
    note: str

    class Config:
        from_attributes = True
