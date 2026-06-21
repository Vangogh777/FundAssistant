from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, DateTime, JSON, Boolean, Text
from app.database import Base


class NotificationChannel(Base):
    """通知渠道配置"""
    __tablename__ = "notification_channels"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False, index=True)

    channel_type = Column(String(20), nullable=False)       # email / feishu / wechat / qq
    # 配置详情
    # email: {"address": "xxx@example.com"}
    # feishu: {"webhook_url": "https://open.feishu.cn/..."}
    # wechat: {"server_chan_key": "SCTxxx"} 或 {"qywx_webhook": "https://qyapi.weixin.qq.com/..."}
    # qq: {"bot_api": "http://...", "qq_number": "..."}
    config = Column(JSON, nullable=False, default=dict)

    is_active = Column(Boolean, default=True)
    notify_on_drip = Column(Boolean, default=True)          # 定投提醒
    notify_on_report = Column(Boolean, default=False)       # 定期报告
    notify_on_alert = Column(Boolean, default=False)        # 涨跌预警

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))


class NotificationLog(Base):
    """通知发送日志"""
    __tablename__ = "notification_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False, index=True)
    channel_type = Column(String(20), nullable=False)
    notify_type = Column(String(30), nullable=False)        # drip_reminder / market_alert / report
    title = Column(String(200), default="")
    content = Column(Text, default="")
    status = Column(String(20), default="pending")           # pending / success / failed
    error_msg = Column(String(500), default="")

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    sent_at = Column(DateTime, nullable=True)
