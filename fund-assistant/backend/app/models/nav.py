from datetime import datetime, timezone
from sqlalchemy import Column, Integer, Float, String, DateTime, JSON
from app.database import Base


class FundNav(Base):
    """基金净值历史"""
    __tablename__ = "fund_navs"

    id = Column(Integer, primary_key=True, index=True)
    fund_code = Column(String(10), nullable=False, index=True)
    date = Column(String(20), nullable=False)             # 日期 YYYY-MM-DD
    nav = Column(Float, default=0.0)                      # 单位净值
    accumulated_nav = Column(Float, default=0.0)           # 累计净值
    daily_change_pct = Column(Float, default=0.0)          # 日涨跌幅 %

    # 多数据源原始数据
    raw_sources = Column(JSON, default=dict)

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    class Meta:
        unique_together = ("fund_code", "date")
