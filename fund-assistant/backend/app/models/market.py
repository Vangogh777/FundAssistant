from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Float, DateTime
from app.database import Base


class MarketIndex(Base):
    """大盘指数行情"""
    __tablename__ = "market_indices"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(20), nullable=False, index=True)            # 指数代码: 000001.SH / 399300.SZ
    name = Column(String(50), nullable=False)                        # 指数名称: 上证指数 / 沪深300
    current_point = Column(Float, default=0.0)                       # 当前点数
    change_pct = Column(Float, default=0.0)                          # 涨跌幅 %
    change_point = Column(Float, default=0.0)                        # 涨跌点数
    open_point = Column(Float, default=0.0)                          # 开盘价
    high_point = Column(Float, default=0.0)                          # 最高价
    low_point = Column(Float, default=0.0)                           # 最低价
    volume = Column(Float, default=0.0)                              # 成交量
    turnover = Column(Float, default=0.0)                            # 成交额

    date = Column(String(20), nullable=False)                        # 日期 YYYY-MM-DD

    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
