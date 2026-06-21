from datetime import datetime, timezone
from sqlalchemy import Column, Integer, Float, DateTime, ForeignKey, String
from sqlalchemy.orm import relationship
from app.database import Base


class Portfolio(Base):
    """用户持仓记录"""
    __tablename__ = "portfolios"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    fund_code = Column(String(10), ForeignKey("funds.code"), nullable=False, index=True)

    shares = Column(Float, nullable=False)               # 持有份额
    cost_per_share = Column(Float, nullable=False)        # 每份成本价（含手续费）
    total_cost = Column(Float, nullable=False)            # 总成本 = shares * cost_per_share
    buy_date = Column(String(20), nullable=False)         # 买入日期 YYYY-MM-DD
    fee = Column(Float, default=0.0)                      # 手续费
    note = Column(String(255), default="")                # 备注

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    user = relationship("User", backref="portfolios")
    fund = relationship("Fund", backref="portfolios")
