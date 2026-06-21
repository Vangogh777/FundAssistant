"""
基金搜索 + 净值 API 路由
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.models.fund import Fund
from app.models.nav import FundNav
from app.schemas.fund import FundResponse, FundSearchResult, FundNavResponse
from app.services.fund_crawler import (
    search_funds, fetch_fund_estimate, fetch_fund_detail,
    fetch_nav_history,
)
from app.utils.auth import get_current_user
from app.models.user import User

router = APIRouter(prefix="/api/funds", tags=["基金数据"])


@router.get("/search", response_model=list[FundSearchResult])
async def search(keyword: str = Query(min_length=1)):
    """搜索基金（按代码或名称）"""
    # 先从天API搜索
    results = await search_funds(keyword)
    if not results:
        # 回退到本地数据库
        return []

    # 为前5条结果补充实时估值
    enriched = []
    for item in results[:10]:
        est = await fetch_fund_estimate(item["code"])
        enriched.append({
            "code": item["code"],
            "name": item["name"],
            "type": item.get("type", ""),
            "nav": est.get("nav", 0) if est else 0,
            "estimate_change_pct": est.get("estimate_change_pct", 0) if est else 0,
        })

    return enriched


@router.get("/{code}/estimate")
async def get_estimate(code: str):
    """获取单只基金实时估值"""
    est = await fetch_fund_estimate(code)
    if not est:
        raise HTTPException(status_code=404, detail="未找到该基金估值数据")
    return est


@router.get("/{code}/detail", response_model=FundResponse)
async def get_fund_detail(
    code: str,
    db: AsyncSession = Depends(get_db),
):
    """获取基金详情（含实时估值）"""
    # 1. 查本地数据库
    result = await db.execute(select(Fund).where(Fund.code == code))
    fund = result.scalar_one_or_none()

    # 2. 从天API获取估值
    est = await fetch_fund_estimate(code)

    if fund:
        if est:
            fund.estimated_nav = est.get("estimated_nav", fund.estimated_nav)
            fund.estimate_change_pct = est.get("estimate_change_pct", fund.estimate_change_pct)
            if est.get("nav"):
                fund.nav = est["nav"]
                fund.nav_date = est.get("nav_date", fund.nav_date)
            await db.commit()
        return fund

    # 3. 如果本地没有，从天API创建
    detail = await fetch_fund_detail(code)
    if not detail and not est:
        raise HTTPException(status_code=404, detail="未找到该基金")

    fund = Fund(
        code=code,
        name=est.get("name", detail.get("name", "") if detail else ""),
        type=detail.get("type", "未知") if detail else "未知",
        company=detail.get("company", "") if detail else "",
        manager=detail.get("manager", "") if detail else "",
        nav=est.get("nav", 0) if est else 0,
        estimated_nav=est.get("estimated_nav", 0) if est else 0,
        estimate_change_pct=est.get("estimate_change_pct", 0) if est else 0,
        nav_date=est.get("nav_date", "") if est else "",
        risk_level=detail.get("risk_level", "") if detail else "",
        fund_scale=detail.get("fund_scale", "") if detail else "",
    )
    db.add(fund)
    await db.commit()
    await db.refresh(fund)
    return fund


@router.get("/{code}/nav", response_model=list[FundNavResponse])
async def get_nav_history(
    code: str,
    days: int = Query(default=30, ge=1, le=365),
    db: AsyncSession = Depends(get_db),
):
    """获取基金历史净值"""
    # 先查本地
    result = await db.execute(
        select(FundNav)
        .where(FundNav.fund_code == code)
        .order_by(FundNav.date.desc())
        .limit(days)
    )
    local = result.scalars().all()

    if len(local) >= days:
        return [{"date": n.date, "nav": n.nav, "accumulated_nav": n.accumulated_nav, "daily_change_pct": n.daily_change_pct}
                for n in reversed(local)]

    # 从天API拉历史
    remote = await fetch_nav_history(code, days)
    if not remote:
        # 返回本地已有的
        return [{"date": n.date, "nav": n.nav, "accumulated_nav": n.accumulated_nav, "daily_change_pct": n.daily_change_pct}
                for n in reversed(local)]

    # 存入本地
    for r in remote:
        exists = await db.execute(
            select(FundNav).where(FundNav.fund_code == code, FundNav.date == r["date"])
        )
        if not exists.scalar_one_or_none():
            db.add(FundNav(
                fund_code=code,
                date=r["date"],
                nav=r["nav"],
                accumulated_nav=r.get("accumulated_nav", 0),
                daily_change_pct=r["daily_change_pct"],
            ))

    await db.commit()

    return [{"date": r["date"], "nav": r["nav"], "accumulated_nav": r.get("accumulated_nav", 0), "daily_change_pct": r["daily_change_pct"]}
            for r in reversed(remote)]
