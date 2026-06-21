"""
市场行情 API 路由
"""
from fastapi import APIRouter
from app.services.fund_crawler import (
    fetch_market_indices, fetch_sector_ranks, fetch_fund_ranks,
    fetch_market_breadth, fetch_finance_news,
)
from app.services.fund_flow import (
    fetch_north_flow, fetch_main_fund_flow, fetch_sector_fund_flow,
)

router = APIRouter(prefix="/api/market", tags=["行情数据"])


@router.get("/indices")
async def get_market_indices():
    """大盘指数行情"""
    return await fetch_market_indices()


@router.get("/sectors")
async def get_sectors():
    """行业板块涨跌排名"""
    return await fetch_sector_ranks()


@router.get("/fund-ranks")
async def get_fund_ranks(period: str = "1m", limit: int = 20):
    """基金收益排行"""
    return await fetch_fund_ranks(period, limit)


@router.get("/north-flow")
async def get_north_flow():
    """北向资金实时流向"""
    return await fetch_north_flow()


@router.get("/main-flow")
async def get_main_flow():
    """主力资金流向"""
    return await fetch_main_fund_flow()


@router.get("/sector-flow")
async def get_sector_flow(top: int = 10):
    """板块资金净流入排行"""
    return await fetch_sector_fund_flow(top)


@router.get("/breadth")
async def get_breadth():
    """市场宽度（涨跌家数）"""
    return await fetch_market_breadth()


@router.get("/news")
async def get_news(limit: int = 15):
    """财经快讯"""
    return await fetch_finance_news(limit)
