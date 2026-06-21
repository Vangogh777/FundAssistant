from datetime import datetime, timezone
from sqlalchemy import Column, Integer, Float, String, DateTime, Boolean
from app.database import Base


class DripPlan(Base):
    """定投计划"""
    __tablename__ = "drip_plans"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False, index=True)
    fund_code = Column(String(10), nullable=False, index=True)

    amount = Column(Float, nullable=False)                  # 每期定投金额
    frequency = Column(String(20), nullable=False)          # 频率: daily/weekly/biweekly/monthly
    day_of_week = Column(Integer, default=1)                # 周几 (1-7, 仅 weekly/biweekly)
    day_of_month = Column(Integer, default=1)               # 每月几号 (1-28, 仅 monthly)
    next_run_date = Column(String(20), nullable=False)      # 下次执行日 YYYY-MM-DD
    is_active = Column(Boolean, default=True)               # 是否启用
    auto_execute = Column(Boolean, default=False)           # 是否自动执行(需对接支付)

    note = Column(String(255), default="")

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
