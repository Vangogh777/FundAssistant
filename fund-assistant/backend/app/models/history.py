"""持仓修改历史记录"""
from datetime import datetime, timezone
from sqlalchemy import Column, Integer, Float, String, DateTime, JSON, ForeignKey
from app.database import Base


class PortfolioHistory(Base):
    __tablename__ = "portfolio_histories"

    id = Column(Integer, primary_key=True, index=True)
    portfolio_id = Column(Integer, ForeignKey("portfolios.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    fund_code = Column(String(10), nullable=False)

    # 变更前后快照
    before_snapshot = Column(JSON, default=dict)   # {"shares": 1000, "cost_per_share": 1.35, ...}
    after_snapshot = Column(JSON, default=dict)    # {"shares": 1500, "cost_per_share": 1.40, ...}

    change_type = Column(String(20), nullable=False)  # create / update / delete
    change_fields = Column(JSON, default=list)        # ["shares", "cost_per_share"]
    note = Column(String(255), default="")

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
