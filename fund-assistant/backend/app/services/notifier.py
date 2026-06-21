"""
通知服务 — 多渠道发送（邮件/飞书/微信/QQ）
"""
import smtplib
import json
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime

import httpx

from app.config import settings


async def send_email(to_address: str, subject: str, body: str) -> dict:
    """发送邮件通知"""
    if not all([settings.SMTP_HOST, settings.SMTP_USER, settings.SMTP_PASS]):
        return {"status": "failed", "error": "SMTP 未配置"}

    try:
        msg = MIMEMultipart()
        msg["From"] = settings.SMTP_USER
        msg["To"] = to_address
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "html"))

        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
            server.starttls()
            server.login(settings.SMTP_USER, settings.SMTP_PASS)
            server.send_message(msg)

        return {"status": "success"}
    except Exception as e:
        return {"status": "failed", "error": str(e)}


async def send_feishu(webhook_url: str, title: str, content: str) -> dict:
    """飞书机器人通知"""
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                webhook_url,
                json={
                    "msg_type": "interactive",
                    "card": {
                        "header": {"title": {"content": title, "tag": "plain_text"}},
                        "elements": [{"tag": "div", "text": {"content": content, "tag": "lark_md"}}],
                    },
                },
                timeout=10,
            )
        data = resp.json()
        return {"status": "success" if data.get("code") == 0 else "failed", "response": data}
    except Exception as e:
        return {"status": "failed", "error": str(e)}


async def send_wechat_serverchan(key: str, title: str, content: str) -> dict:
    """ServerChan (微信) 推送"""
    url = f"https://sctapi.ftqq.com/{key}.send"
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(url, data={"title": title, "desp": content}, timeout=10)
        data = resp.json()
        return {"status": "success" if data.get("code") == 0 else "failed", "response": data}
    except Exception as e:
        return {"status": "failed", "error": str(e)}


async def send_notification(
    channel_type: str,
    config: dict,
    title: str,
    content: str,
) -> dict:
    """统一发送入口"""
    handlers = {
        "email": lambda: send_email(config.get("address", ""), title, content),
        "feishu": lambda: send_feishu(config.get("webhook_url", ""), title, content),
        "wechat": lambda: send_wechat_serverchan(config.get("server_chan_key", ""), title, content),
        "qq": lambda: send_feishu(config.get("webhook_url", ""), title, content),  # QQ 也通过 webhook 推送
    }
    handler = handlers.get(channel_type)
    if not handler:
        return {"status": "failed", "error": f"不支持的渠道: {channel_type}"}
    return await handler()
