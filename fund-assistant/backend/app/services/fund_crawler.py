"""
天天基金数据爬虫 — 基金实时估值、历史净值、搜索、大盘行情
数据源：eastmoney.com（天天基金）
目标：净值估算结果与 "净值估算助手" 小程序完全一致
"""
import re
import json
import time
from datetime import datetime, timedelta
from typing import Optional
import httpx
from bs4 import BeautifulSoup

# ============================================================
# 公用 HTTP 客户端（复用连接，设置合理的 UA）
# ============================================================
_client: Optional[httpx.AsyncClient] = None

def get_client() -> httpx.AsyncClient:
    global _client
    if _client is None or _client.is_closed:
        _client = httpx.AsyncClient(
            timeout=httpx.Timeout(15.0),
            headers={
                "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) "
                              "AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148",
                "Referer": "https://fundf10.eastmoney.com/",
            },
        )
    return _client


# ============================================================
# 1. 基金实时估值（核心 — 与净值估算助手一致）
# ============================================================
# 数据来源：天天基金实时估值接口 http://fundgz.1234567.com.cn/js/{code}.js
# 返回 JSONP 格式: jsonpgz({...})
# 字段：fundcode, name, jzrq(净值日期), dwjz(单位净值), gsz(估算净值),
#       gszzl(估算涨跌%), gztime(估值时间)

async def fetch_fund_estimate(code: str) -> dict | None:
    """获取单只基金的实时估算净值"""
    url = f"http://fundgz.1234567.com.cn/js/{code}.js?rt={int(time.time() * 1000)}"
    try:
        resp = await get_client().get(url)
        resp.raise_for_status()
        text = resp.text
        # 解析 JSONP: jsonpgz({...})
        match = re.search(r"jsonpgz\((\{.*?\})\)", text, re.DOTALL)
        if not match:
            return None
        data = json.loads(match.group(1))
        return {
            "code": data.get("fundcode", code),
            "name": data.get("name", ""),
            "nav_date": data.get("jzrq", ""),
            "nav": float(data.get("dwjz", 0)),
            "estimated_nav": float(data.get("gsz", 0)),
            "estimate_change_pct": float(data.get("gszzl", 0)),
            "estimate_time": data.get("gztime", ""),
        }
    except Exception:
        return None


# 判断当前时间是否适合使用官方净值（盘后 ≥18:00 或非交易日）
def is_after_market_close() -> bool:
    """判断是否已过收盘且净值应该已公布"""
    now = datetime.now()
    # 非交易日：全天都应该是官方净值
    # 交易日：15:00 收盘，一般 18:00-22:00 净值陆续公布
    hour = now.hour
    weekday = now.weekday()
    if weekday >= 5:  # 周六日
        return True
    return hour >= 18


async def fetch_latest_actual_nav(code: str) -> dict | None:
    """获取基金最新官方确认净值（非估算），从历史净值接口获取"""
    try:
        history = await fetch_nav_history(code, days=10)
        if not history:
            return None
        latest = history[0]  # fetch_nav_history 按日期降序排列
        return {
            "code": code,
            "nav_date": latest["date"],
            "nav": latest["nav"],
            "accumulated_nav": latest.get("accumulated_nav", latest["nav"]),
            "daily_change_pct": latest.get("daily_change_pct", 0),
            "source": "actual",  # 标记为官方净值
        }
    except Exception:
        return None


async def fetch_multi_estimate(codes: list[str]) -> list[dict]:
    """批量获取多只基金的实时估值"""
    import asyncio
    tasks = [fetch_fund_estimate(c) for c in codes]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    return [r for r in results if isinstance(r, dict) and r is not None]


# ============================================================
# 2. 基金详情 / 搜索
# ============================================================
async def fetch_fund_detail(code: str) -> dict | None:
    """获取基金详细信息（规模/类型/管理人/风险等级）"""
    url = f"https://fundgz.1234567.com.cn/static/api/Fund/{code}.json"
    try:
        resp = await get_client().get(url)
        resp.raise_for_status()
        data = resp.json()
        return {
            "code": data.get("code", code),
            "name": data.get("name", ""),
            "type": data.get("type", ""),
            "company": data.get("company", ""),
            "manager": data.get("manager", ""),
            "establish_date": data.get("establish_date", ""),
            "risk_level": data.get("risk_level", "中风险"),
            "fund_scale": data.get("fund_scale", ""),
            "description": data.get("description", ""),
        }
    except Exception:
        return None


async def search_funds(keyword: str) -> list[dict]:
    """搜索基金（模糊匹配代码或名称）"""
    url = "https://fundsuggest.eastmoney.com/FundSearch/api/FundSearchAPI.ashx"
    params = {"m": "1", "key": keyword}
    try:
        resp = await get_client().get(url, params=params)
        resp.raise_for_status()
        data = resp.json()
        if data.get("ErrCode") != 0:
            return []
        funds = []
        for item in data.get("Datas", []):
            code = item.get("CODE", "")
            name = item.get("NAME", "")
            info = item.get("FundBaseInfo", {})
            if code and name:
                funds.append({
                    "code": code,
                    "name": name,
                    "type": info.get("FTYPE", ""),
                    "nav": float(info.get("DWJZ", 0)),
                })
        return funds
    except Exception:
        return []


# ============================================================
# 3. 基金历史净值
# ============================================================
async def fetch_nav_history(code: str, days: int = 60) -> list[dict]:
    """获取基金历史净值数据"""
    # 计算页数：每页 20 条
    page_size = 20
    pages = max(1, (days + page_size - 1) // page_size)

    all_records = []
    for page in range(1, pages + 1):
        url = f"https://api.fund.eastmoney.com/f10/lsjz"
        params = {
            "fundCode": code,
            "pageIndex": page,
            "pageSize": page_size,
            "startDate": "",
            "endDate": "",
            "_": int(time.time() * 1000),
        }
        headers = {"Referer": f"https://fundf10.eastmoney.com/jjjz_{code}.html"}
        try:
            resp = await get_client().get(url, params=params, headers=headers)
            resp.raise_for_status()
            data = resp.json()
            records = data.get("Data", {}).get("LSJZList", [])
            if not records:
                break
            for r in records:
                all_records.append({
                    "date": r.get("FSRQ", ""),
                    "nav": float(r.get("DWJZ", 0)),
                    "accumulated_nav": float(r.get("LJJZ", 0)),
                    "daily_change_pct": r.get("JZZZL", ""),  # 有时候是百分比字符串
                })
        except Exception:
            break

    # 解析百分比字符串
    for r in all_records:
        pct = r["daily_change_pct"]
        if isinstance(pct, str) and pct.strip():
            try:
                r["daily_change_pct"] = float(pct.strip("%"))
            except ValueError:
                r["daily_change_pct"] = 0.0
        else:
            r["daily_change_pct"] = float(pct) if pct else 0.0

    return all_records


# ============================================================
# 4. 大盘指数行情（东方财富）
# ============================================================
INDEX_MAP = [
    ("1.000001", "上证指数"),
    ("0.399300", "沪深300"),
    ("0.399006", "创业板指"),
    ("1.000688", "科创50"),
    ("1.000016", "上证50"),
    ("0.399001", "深证成指"),
    ("0.399005", "中小100"),
]


async def fetch_market_indices() -> list[dict]:
    """获取大盘指数行情 — 东方财富批量接口"""
    secids = ",".join(f"{code}" for code, _ in INDEX_MAP)
    url = "https://push2.eastmoney.com/api/qt/ulist.np/get"
    params = {
        "fltt": "2",
        "secids": secids,
        "fields": "f2,f3,f4,f12,f14,f15,f16,f17,f18",
        "_": str(int(time.time() * 1000)),
    }
    try:
        resp = await get_client().get(url, params=params)
        resp.raise_for_status()
        data = resp.json()
        results = []
        name_map = dict(INDEX_MAP)
        for item in data.get("data", {}).get("diff", []):
            code = item.get("f12", "")
            results.append({
                "code": code,
                "name": name_map.get(code, item.get("f14", "")),
                "current_point": float(item.get("f2", 0) or 0),
                "change_pct": float(item.get("f3", 0) or 0),
                "change_point": float(item.get("f4", 0) or 0),
                "high_point": float(item.get("f15", 0) or 0),
                "low_point": float(item.get("f16", 0) or 0),
                "open_point": float(item.get("f17", 0) or 0),
                "date": datetime.now().strftime("%Y-%m-%d"),
            })
        return results
    except Exception:
        return []


# ============================================================
# 5. 热门板块 / 行业涨跌榜
# ============================================================
async def fetch_sector_ranks() -> list[dict]:
    """获取行业板块涨跌幅排名"""
    url = "https://push2.eastmoney.com/api/qt/clist/get"
    params = {
        "pn": "1",
        "pz": "20",
        "po": "1",
        "np": "1",
        "fltt": "2",
        "invt": "2",
        "fid": "f3",
        "fs": "m:90+t2",
        "fields": "f2,f3,f4,f12,f14",
        "_": int(time.time() * 1000),
    }
    try:
        resp = await get_client().get(url, params=params)
        resp.raise_for_status()
        data = resp.json()
        ranks = []
        for item in data.get("data", {}).get("diff", []):
            ranks.append({
                "code": item.get("f12", ""),
                "name": item.get("f14", ""),
                "price": float(item.get("f2", 0) or 0),
                "change_pct": float(item.get("f3", 0) or 0),
                "volume": float(item.get("f4", 0) or 0),
            })
        return ranks
    except Exception:
        return []


# ============================================================
# 6. 基金排行（近1月/3月/6月/1年）
# ============================================================
async def fetch_fund_ranks(period: str = "1m", limit: int = 20) -> list[dict]:
    """基金收益排行"""
    period_map = {"1m": "r", "3m": "three", "6m": "six", "1y": "one", "all": "all"}
    p = period_map.get(period, "r")

    url = "https://api.fund.eastmoney.com/data/rank"
    params = {
        "sc": p,
        "st": "desc",
        "pn": "1",
        "ps": str(limit),
        "ft": "all",
        "_": int(time.time() * 1000),
    }
    headers = {"Referer": "https://fund.eastmoney.com/data/fundranking.html"}
    try:
        resp = await get_client().get(url, params=params, headers=headers)
        resp.raise_for_status()
        data = resp.json()
        ranks = []
        for item in data.get("Data", []):
            try:
                ranks.append({
                    "code": item.get("fundCode", ""),
                    "name": item.get("fundName", ""),
                    "return_1m": float(item.get("ret1", 0) or 0),
                    "return_3m": float(item.get("ret3", 0) or 0),
                    "return_6m": float(item.get("ret6", 0) or 0),
                    "return_1y": float(item.get("ret1y", 0) or 0),
                    "type": item.get("fundType", ""),
                })
            except (ValueError, TypeError):
                continue
        return ranks
    except Exception:
        return []


# ============================================================
# 7. 市场宽度（涨跌家数）
# ============================================================
async def fetch_market_breadth() -> dict:
    """获取全市场涨跌家数"""
    url = "https://push2.eastmoney.com/api/qt/ulist.np/get"
    params = {
        "fltt": "2",
        "secids": "1.000001,0.399001",
        "fields": "f170,f171,f172",
        "_": str(int(time.time() * 1000)),
    }
    try:
        resp = await get_client().get(url, params=params)
        data = resp.json()
        total_up = 0
        total_down = 0
        for item in data.get("data", {}).get("diff", []):
            total_up += int(item.get("f170", 0) or 0)
            total_down += int(item.get("f171", 0) or 0)
        return {"up": total_up, "down": total_down, "flat": 0}
    except Exception:
        return {"up": 0, "down": 0, "flat": 0}


# ============================================================
# 8. 财经快讯
# ============================================================
async def fetch_finance_news(limit: int = 15) -> list[dict]:
    """获取东方财富快讯"""
    url = "https://push2.eastmoney.com/api/qt/stock/get"
    params = {
        "secid": "1.000001",
        "fields": "f58,f57",
        "_": str(int(time.time() * 1000)),
    }
    # 改用 RSS + 头条
    news_url = "https://newsapi.eastmoney.com/kuaixun/v1/getlist_101_1_0_1_0_0_0"
    try:
        resp = await get_client().get(news_url, params={"_": str(int(time.time() * 1000))})
        data = resp.json()
        articles = data.get("data", {}).get("list", [])
        news = []
        for a in articles[:limit]:
            news.append({
                "title": a.get("title", ""),
                "time": a.get("showTime", ""),
                "url": f"https://finance.eastmoney.com/a/{a.get('code','')}.html",
            })
        return news
    except Exception:
        return []
