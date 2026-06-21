"""
基金持仓穿透分析 — 十大重仓股 + 行业分布
"""
import re
import json
import time
from typing import Optional
import httpx


async def _get_json(url: str, referer: str = "") -> dict:
    headers = {"Referer": referer} if referer else {}
    try:
        async with httpx.AsyncClient(timeout=15) as c:
            r = await c.get(url, headers=headers)
            if r.status_code == 200:
                return r.json()
            return {}
    except Exception:
        return {}


async def fetch_fund_holdings(code: str, top: int = 10) -> dict:
    """
    获取基金前N大重仓股
    返回: 股票列表 + 占比
    """
    url = f"https://fundf10.eastmoney.com/FundArchivesDatas.aspx"
    params = {
        "type": "jjcc",
        "code": code,
        "topline": str(top),
        "year": "",
        "month": "",
        "rt": str(int(time.time() * 1000)),
    }
    referer = f"https://fundf10.eastmoney.com/ccmx_{code}.html"

    try:
        async with httpx.AsyncClient(timeout=15) as c:
            r = await c.get(url, params=params, headers={
                "Referer": referer,
                "User-Agent": "Mozilla/5.0",
            })
            raw = r.text

        # 响应是 JS 变量赋值: var apidata={ content:"<html>..." }
        html = raw
        match = re.search(r'content:\"(.*?)\";\s*\}', raw, re.DOTALL)
        if match:
            html = match.group(1)

        stocks = []
        # 匹配 <td class="...">股票代码</td> 后面的 <td>股票名称</td> 等
        td_pattern = re.findall(r'<td[^>]*>(.*?)</td>', html, re.DOTALL)
        # 每7个td为一组（序号,代码,名称,?,?,占比,?）
        for i in range(0, len(td_pattern) - 6, 7):
            code_cell = re.sub(r'<.*?>', '', td_pattern[i] if i < len(td_pattern) else '')
            name_cell = re.sub(r'<.*?>', '', td_pattern[i+1] if i+1 < len(td_pattern) else '')
            # 占比通常在第6列(index 5)
            ratio_cell = ' '.join(td_pattern[max(0,i+4):min(len(td_pattern),i+7)])
            code_m = re.search(r'(\d{6})', code_cell)
            ratio_m = re.search(r'([\d.]+)%', ratio_cell)
            if code_m and ratio_m and float(ratio_m.group(1)) > 0:
                stocks.append({
                    "code": code_m.group(1),
                    "name": name_cell.strip() or code_m.group(1),
                    "ratio": float(ratio_m.group(1)),
                })
            if len(stocks) >= top:
                break

        return {
            "fund_code": code,
            "top_holdings": stocks[:top] if stocks else [],
            "total_stocks_count": len(stocks),
        }
    except Exception:
        return {"fund_code": code, "top_holdings": [], "total_stocks_count": 0}


async def fetch_fund_sector_allocation(code: str) -> dict:
    """
    获取基金行业配置（资产配置）
    """
    url = f"https://fundf10.eastmoney.com/FundArchivesDatas.aspx"
    params = {
        "type": "zcpz",
        "code": code,
        "rt": str(int(time.time() * 1000)),
    }
    referer = f"https://fundf10.eastmoney.com/zcpz_{code}.html"

    try:
        async with httpx.AsyncClient(timeout=15) as c:
            r = await c.get(url, params=params, headers={"Referer": referer})
            text = r.text

        # 解析资产配置比例
        allocation = {}
        # 股票占比
        stock_match = re.search(r'股票[^<]*?(\d+\.?\d*)%', text)
        if stock_match:
            allocation["stock"] = float(stock_match.group(1))
        bond_match = re.search(r'债券[^<]*?(\d+\.?\d*)%', text)
        if bond_match:
            allocation["bond"] = float(bond_match.group(1))
        cash_match = re.search(r'现金[^<]*?(\d+\.?\d*)%', text)
        if cash_match:
            allocation["cash"] = float(cash_match.group(1))

        return {
            "fund_code": code,
            "allocation": allocation if allocation else {"stock": 0, "bond": 0, "cash": 0, "other": 0},
        }
    except Exception:
        return {"fund_code": code, "allocation": {}}


async def fetch_stock_brief(code: str) -> dict:
    """获取个股简要行情"""
    url = f"https://push2.eastmoney.com/api/qt/stock/get"
    params = {
        "secid": f"0.{code}" if code.startswith("0") or code.startswith("3") else f"1.{code}",
        "fields": "f43,f44,f45,f46,f47,f48,f50,f57,f58,f170",
        "rt": str(int(time.time() * 1000)),
    }
    try:
        data = await _get_json(f"{url}?secid={params['secid']}&fields={params['fields']}", "")
        d = data.get("data", {})
        if d:
            return {
                "code": code,
                "name": d.get("f58", ""),
                "price": d.get("f43", 0) / 100 if d.get("f43") else 0,
                "change_pct": d.get("f170", 0) / 100 if d.get("f170") else 0,
                "high": d.get("f44", 0) / 100 if d.get("f44") else 0,
                "low": d.get("f45", 0) / 100 if d.get("f45") else 0,
                "volume": d.get("f47", 0),
                "turnover": d.get("f48", 0),
            }
    except Exception:
        pass
    return {"code": code, "name": "", "price": 0, "change_pct": 0}
