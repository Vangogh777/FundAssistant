from datetime import datetime, timezone
from sqlalchemy import Column, Integer, Float, String, DateTime
from app.database import Base


class Dividend(Base):
    """分红记录"""
    __tablename__ = "dividends"

    id = Column(Integer, primary_key=True, index=True)
    fund_code = Column(String(10), nullable=False, index=True)
    date = Column(String(20), nullable=False)              # 除息日 YYYY-MM-DD
    dividend_per_share = Column(Float, nullable=False)      # 每份分红金额
    dividend_type = Column(String(20), default="现金分红")   # 分红方式: 现金分红/红利再投资

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
