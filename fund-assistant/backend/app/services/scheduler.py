"""
定时任务调度器 — 定投提醒扫描 + 每日行情推送
"""
from datetime import datetime, date, timedelta

from app.database import async_session_factory
from app.models.drip import DripPlan
from app.models.notification import NotificationChannel, NotificationLog
from app.services.notifier import send_notification
from sqlalchemy import select


def get_next_run_date(frequency: str, day_of_week: int, day_of_month: int) -> str:
    """根据频率计算下次执行日"""
    today = date.today()
    if frequency == "daily":
        return (today + timedelta(days=1)).isoformat()
    elif frequency == "weekly":
        # 下周指定的 day_of_week
        days_ahead = (day_of_week - 1 - today.weekday()) % 7
        if days_ahead == 0:
            days_ahead = 7
        return (today + timedelta(days=days_ahead)).isoformat()
    elif frequency == "biweekly":
        days_ahead = (day_of_week - 1 - today.weekday()) % 7
        if days_ahead == 0:
            days_ahead = 7
        return (today + timedelta(days=days_ahead + 7)).isoformat()
    elif frequency == "monthly":
        # 下月指定 day_of_month
        next_month = today.month % 12 + 1
        next_year = today.year + (1 if next_month == 1 else 0)
        try:
            return date(next_year, next_month, min(day_of_month, 28)).isoformat()
        except ValueError:
            return date(next_year, next_month, 28).isoformat()
    return (today + timedelta(days=1)).isoformat()


async def scan_drip_reminders():
    """扫描到期的定投计划并发送通知"""
    today_str = date.today().isoformat()

    async with async_session_factory() as db:
        # 查找今天到期的计划
        result = await db.execute(
            select(DripPlan).where(
                DripPlan.is_active == True,
                DripPlan.next_run_date == today_str,
            )
        )
        plans = result.scalars().all()

        for plan in plans:
            # 获取用户的活跃通知渠道
            ch_result = await db.execute(
                select(NotificationChannel).where(
                    NotificationChannel.user_id == plan.user_id,
                    NotificationChannel.is_active == True,
                    NotificationChannel.notify_on_drip == True,
                )
            )
            channels = ch_result.scalars().all()

            title = "💰 定投提醒"
            content = f"🔔 今天是基金 {plan.fund_code} 的定投日！\n建议定投金额: ¥{plan.amount}\n— 基金智能助手"

            for ch in channels:
                result = await send_notification(ch.channel_type, ch.config, title, content)
                # 记录日志
                log = NotificationLog(
                    user_id=plan.user_id,
                    channel_type=ch.channel_type,
                    notify_type="drip_reminder",
                    title=title,
                    content=content,
                    status=result.get("status", "failed"),
                    error_msg=result.get("error", "") if result.get("status") == "failed" else "",
                    sent_at=datetime.utcnow(),
                )
                db.add(log)

            # 计算下次执行日
            plan.next_run_date = get_next_run_date(
                plan.frequency, plan.day_of_week, plan.day_of_month
            )

        await db.commit()


# 定时任务启动（由 APScheduler 调用）
async def start_scheduler():
    """在 FastAPI 启动时注册定时扫描任务"""
    from apscheduler.schedulers.asyncio import AsyncIOScheduler
    scheduler = AsyncIOScheduler()

    # 每天 9:00 扫描定投提醒
    scheduler.add_job(scan_drip_reminders, "cron", hour=9, minute=0, id="drip_reminder")

    # 每个交易日 9:30-15:00 每5分钟更新行情（可选）
    # scheduler.add_job(update_market, "cron", hour="9-15", minute="*/5", id="market_update")

    scheduler.start()
    return scheduler
