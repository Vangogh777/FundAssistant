"""
大盘资金流向 — 北向资金 / 主力净流入 / 板块资金
"""
import re
import json
import time
from typing import Optional
import httpx


async def _get_json(url: str, headers: Optional[dict] = None) -> dict:
    """安全的 HTTP GET JSON"""
    try:
        async with httpx.AsyncClient(timeout=10) as c:
            r = await c.get(url, headers=headers or {})
            return r.json() if r.status_code == 200 else {}
    except Exception:
        return {}


# ============================================================
# 1. 北向资金（沪股通+深股通）
# ============================================================
async def fetch_north_flow() -> dict:
    """
    北向资金实时流向
    数据源：东方财富
    """
    url = "https://push2.eastmoney.com/api/qt/kamt.kline/get"
    params = {
        "fields1": "f1,f2,f3,f4",
        "fields2": "f51,f52,f53,f54,f55",
        "klt": "1",
        "lmt": "1",
        "_": int(time.time() * 1000),
    }
    headers = {"Referer": "https://data.eastmoney.com/hsgt/index.html"}

    try:
        async with httpx.AsyncClient(timeout=10) as c:
            r = await c.get(url, params=params, headers=headers)
            data = r.json()

        if not data or not data.get("data"):
            return {"status": "no_data"}

        hgt = data["data"].get("s2n", [])  # 沪股通
        sgt = data["data"].get("s2n", [])  # 深股通 (实际结构可能不同)

        # 取最新一条
        items = data["data"].get("s2n", [])
        if not items:
            return {"status": "no_data"}

        latest = items[-1]  # f51=日期, f52=当日净流入(亿)
        parts = latest.split(",")
        if len(parts) >= 4:
            return {
                "date": parts[0],
                "net_flow_yi": float(parts[1] or 0),     # 当日净流入(亿)
                "balance_yi": float(parts[2] or 0),       # 累计净流入(亿)
                "shanghai_flow": float(parts[3] or 0),    # 沪股通
                "shenzhen_flow": float(parts[4] or 0) if len(parts) > 4 else 0,  # 深股通
            }

        return {"status": "parse_error"}
    except Exception:
        return {"status": "fetch_error"}


# ============================================================
# 2. 主力资金流向（大盘）
# ============================================================
async def fetch_main_fund_flow() -> dict:
    """
    今日主力资金净流入
    数据源：东方财富全市场资金流向
    """
    url = "https://push2.eastmoney.com/api/qt/stock/fflow/daykline/get"
    params = {
        "lmt": "1",
        "klt": "1",
        "secid": "1.000001",  # 上证指数
        "fields1": "f1,f2,f3,f7",
        "fields2": "f51,f52,f53,f54,f55,f56,f57,f58",
        "_": int(time.time() * 1000),
    }
    headers = {"Referer": "https://data.eastmoney.com/zjlx/"}

    try:
        async with httpx.AsyncClient(timeout=10) as c:
            r = await c.get(url, params=params, headers=headers)
            data = r.json()

        if not data or not data.get("data") or not data["data"].get("klines"):
            return {"status": "no_data"}

        latest = data["data"]["klines"][-1]
        parts = latest.split(",")
        # f51=日期, f52=主力净流入(元), f53=小单, f54=中单, f55=大单, f56=超大单
        if len(parts) >= 6:
            return {
                "date": parts[0],
                "main_net_flow_yi": round(float(parts[1] or 0) / 1e8, 2),    # 主力净流入(亿)
                "small_order_yi": round(float(parts[2] or 0) / 1e8, 2),
                "mid_order_yi": round(float(parts[3] or 0) / 1e8, 2),
                "big_order_yi": round(float(parts[4] or 0) / 1e8, 2),
                "super_big_yi": round(float(parts[5] or 0) / 1e8, 2),
            }
        return {"status": "parse_error"}
    except Exception:
        return {"status": "fetch_error"}


# ============================================================
# 3. 行业板块资金流向
# ============================================================
async def fetch_sector_fund_flow(top_n: int = 10) -> list:
    """板块资金净流入排行"""
    url = "https://push2.eastmoney.com/api/qt/clist/get"
    params = {
        "pn": "1",
        "pz": str(top_n),
        "po": "1",
        "np": "1",
        "fltt": "2",
        "invt": "2",
        "fid": "f62",          # 按主力净流入排序
        "fs": "m:90+t2",
        "fields": "f2,f3,f4,f12,f14,f62,f184,f66",
        "_": int(time.time() * 1000),
    }
    try:
        async with httpx.AsyncClient(timeout=10) as c:
            r = await c.get(url, params=params)
            data = r.json()

        results = []
        for item in data.get("data", {}).get("diff", []):
            net_flow = float(item.get("f62", 0) or 0)  # 主力净流入(元)
            results.append({
                "code": item.get("f12", ""),
                "name": item.get("f14", ""),
                "price": float(item.get("f2", 0) or 0),
                "change_pct": float(item.get("f3", 0) or 0),
                "net_flow_yi": round(net_flow / 1e8, 2),   # 转为亿
                "net_flow_1d_yi": round(float(item.get("f184", 0) or 0) / 1e8, 2),
                "net_flow_5d_yi": round(float(item.get("f66", 0) or 0) / 1e8, 2),
            })
        return results
    except Exception:
        return []
