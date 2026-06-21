"""
定投计划 + 通知渠道 API 路由
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List

from app.database import get_db
from app.models.user import User
from app.models.drip import DripPlan
from app.models.notification import NotificationChannel, NotificationLog
from app.schemas.fund import DripPlanCreate, DripPlanResponse
from app.utils.auth import get_current_user

router = APIRouter(tags=["定投&通知"])


# ============ 定投计划 ============
@router.get("/api/drip", response_model=list[DripPlanResponse])
async def list_drip_plans(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(DripPlan).where(DripPlan.user_id == current_user.id).order_by(DripPlan.next_run_date.asc())
    )
    plans = result.scalars().all()
    return plans


@router.post("/api/drip", response_model=DripPlanResponse)
async def create_drip_plan(
    data: DripPlanCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    plan = DripPlan(
        user_id=current_user.id,
        fund_code=data.fund_code,
        amount=data.amount,
        frequency=data.frequency,
        day_of_week=data.day_of_week,
        day_of_month=data.day_of_month,
        next_run_date=data.next_run_date,
        note=data.note,
    )
    db.add(plan)
    await db.commit()
    await db.refresh(plan)
    return plan


@router.put("/api/drip/{plan_id}")
async def update_drip_plan(plan_id: int, data: dict, current_user=Depends(get_current_user), db=Depends(get_db)):
    result = await db.execute(select(DripPlan).where(DripPlan.id == plan_id, DripPlan.user_id == current_user.id))
    plan = result.scalar_one_or_none()
    if not plan:
        raise HTTPException(status_code=404)
    for k, v in data.items():
        if hasattr(plan, k):
            setattr(plan, k, v)
    await db.commit()
    return {"message": "ok"}


@router.delete("/api/drip/{plan_id}")
async def delete_drip_plan(plan_id: int, current_user=Depends(get_current_user), db=Depends(get_db)):
    result = await db.execute(select(DripPlan).where(DripPlan.id == plan_id, DripPlan.user_id == current_user.id))
    plan = result.scalar_one_or_none()
    if not plan:
        raise HTTPException(status_code=404)
    await db.delete(plan)
    await db.commit()
    return {"message": "删除成功"}


# ============ 通知渠道 ============
@router.get("/api/notification/channels")
async def list_channels(current_user=Depends(get_current_user), db=Depends(get_db)):
    result = await db.execute(
        select(NotificationChannel).where(NotificationChannel.user_id == current_user.id)
    )
    return result.scalars().all()


@router.post("/api/notification/channels")
async def create_channel(
    data: dict,
    current_user=Depends(get_current_user),
    db=Depends(get_db),
):
    channel = NotificationChannel(
        user_id=current_user.id,
        channel_type=data["channel_type"],
        config=data.get("config", {}),
    )
    db.add(channel)
    await db.commit()
    await db.refresh(channel)
    return channel


@router.delete("/api/notification/channels/{channel_id}")
async def delete_channel(channel_id: int, current_user=Depends(get_current_user), db=Depends(get_db)):
    result = await db.execute(
        select(NotificationChannel).where(NotificationChannel.id == channel_id, NotificationChannel.user_id == current_user.id)
    )
    ch = result.scalar_one_or_none()
    if not ch:
        raise HTTPException(status_code=404)
    await db.delete(ch)
    await db.commit()
    return {"message": "删除成功"}
