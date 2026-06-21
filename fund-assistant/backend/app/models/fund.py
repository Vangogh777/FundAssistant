from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Float, DateTime, Text, JSON
from app.database import Base


class Fund(Base):
    """基金基础信息表"""
    __tablename__ = "funds"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(10), unique=True, nullable=False, index=True)      # 基金代码，如 "000001"
    name = Column(String(100), nullable=False)                              # 基金名称
    type = Column(String(30), default="混合型")                              # 类型: 股票型/混合型/债券型/货币型/指数型/QDII
    company = Column(String(100), default="")                               # 基金公司
    manager = Column(String(50), default="")                                # 基金经理
    establish_date = Column(String(20), default="")                         # 成立日期
    nav = Column(Float, default=0.0)                                        # 最新单位净值
    accumulated_nav = Column(Float, default=0.0)                            # 最新累计净值
    estimated_nav = Column(Float, default=0.0)                              # 今日估算净值
    estimate_change_pct = Column(Float, default=0.0)                        # 估算涨跌幅 %
    nav_date = Column(String(20), default="")                               # 净值日期
    risk_level = Column(String(10), default="中风险")                        # 风险等级
    fund_scale = Column(String(50), default="")                             # 基金规模
    description = Column(Text, default="")                                  # 基金简介
    # 多数据源均衡估值 (JSON: {"eastmoney": 1.234, "fundsite": 1.235, "weighted": 1.2345})
    multi_source_data = Column(JSON, default=dict)

    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
