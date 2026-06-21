"""
OCR 图片识别 — 支持支付宝/天天基金等持仓截图
直接用 tesseract CLI 调用，绕过 Python 依赖冲突
"""
import re
import io
import subprocess
import tempfile
import os
from fastapi import APIRouter, UploadFile, File, Depends
from fastapi.responses import JSONResponse
from app.utils.auth import get_current_user
from app.models.user import User

router = APIRouter(prefix="/api/ocr", tags=["OCR识别"])


# ====== 文本提取：直接用 tesseract 命令行 ======

def _ocr_tesseract_cli(file_bytes: bytes) -> str:
    """调用 tesseract CLI + 图像预处理 + 多模式"""
    tmp_path = None
    try:
        # 预处理：转灰度 + 放大 + 锐化
        try:
            from PIL import Image, ImageEnhance, ImageFilter
            img = Image.open(io.BytesIO(file_bytes)).convert('L')
            w, h = img.size
            if max(w, h) < 1000:
                scale = 2
                img = img.resize((int(w * scale), int(h * scale)), Image.LANCZOS)
            img = ImageEnhance.Contrast(img).enhance(2.0)
            img = ImageEnhance.Sharpness(img).enhance(1.5)
            # 二值化
            img = img.point(lambda x: 0 if x < 140 else 255)
            buf = io.BytesIO()
            img.save(buf, 'PNG')
            file_bytes = buf.getvalue()
        except Exception:
            pass

        with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp:
            tmp.write(file_bytes)
            tmp_path = tmp.name

        # 尝试多种 PSM 模式
        best = ''
        for psm in ['3', '4', '6']:
            result = subprocess.run(
                ['tesseract', tmp_path, 'stdout', '-l', 'chi_sim+eng', '--psm', psm],
                capture_output=True, text=True, timeout=30
            )
            text = result.stdout.strip()
            if len(text) > len(best):
                best = text

        if tmp_path:
            os.unlink(tmp_path)
        return best
    except FileNotFoundError:
        if tmp_path and os.path.exists(tmp_path):
            os.unlink(tmp_path)
        return ''
    except Exception:
        if tmp_path and os.path.exists(tmp_path):
            os.unlink(tmp_path)
        return ''


# ====== 解析逻辑（针对支付宝/天天基金截图优化）======

# 6位基金代码
FUND_CODE_RE = re.compile(r'\b(\d{6})\b')

# 金额：￥12,345.67 或 ¥ 12,345.67 或 +123.45 或 -123.45
MONEY_RE = re.compile(r'[¥￥]?\s*([+-]?\d{1,3}(?:,\d{3})*\.?\d{0,2})')

# 收益率：+12.34% 或 -5.67%
PCT_RE = re.compile(r'([+-]?\d+\.?\d*)\s*%')

# 份额
SHARES_RE = re.compile(r'(\d{1,3}(?:,\d{3})*(?:\.\d+)?)\s*(?:份|持有份额)')


def parse_fund_from_text(text: str) -> dict:
    """从 OCR 文本提取基金持仓信息，适配支付宝/微信截图"""
    lines = [l.strip() for l in text.split('\n') if l.strip()]

    # 第一步：过滤垃圾行
    skip_words = ['去看看', '基金市场', '机会', '自选', '公告', '产品提醒',
                  '财富号', '存储巨头', '营收净利', '定投', '持有收益排序',
                  '名称', '金额/昨日收益', '持有收益/率',
                  '我的持有', '去看看']
    # 整行匹配的短标签（不做子串匹配，避免误杀基金名）
    exact_skip = {'全部', '黄金', '全球', '偏股', '偏债', '指数', '基金', '持有'}
    clean_lines = [l for l in lines
                   if not any(kw in l for kw in skip_words)
                   and l not in exact_skip]

    # 第二步：扫描基金数据块
    # 支付宝格式：基金名 → 金额行 → +收益行 → +收益率%
    # 也可能金额和收益合并在一行

    funds: list[dict] = []
    i = 0
    while i < len(clean_lines):
        line = clean_lines[i]

        # 检测行内是否嵌有金额（基金名+金额粘在一起，如"华夏移动互联灵活配置混合6,633.29"）
        inline_match = re.match(r'^([\u4e00-\u9fffA-Za-z()（）]+?)\s*(\d{1,3}(?:,\d{3})*\.?\d{1,2})$', line)
        if inline_match and len(inline_match.group(1)) >= 4:
            fund_name = inline_match.group(1).strip()
            market_val = float(inline_match.group(2).replace(',', ''))
            # 找收益
            profit = 0.0
            for j in range(i + 1, min(i + 3, len(clean_lines))):
                sign = re.match(r'^([+\-])\s*(\d{1,3}(?:,\d{3})*\.?\d{1,2})$', clean_lines[j])
                if sign:
                    profit = float(sign.group(2).replace(',', ''))
                    if sign.group(1) == '-': profit = -profit
                    break
            # 如果前一行是纯英文/符号（如 "QDII)A"），拼到基金名上
            prev_line = clean_lines[i-1] if i >= 1 else ''
            prev2 = clean_lines[i-2] if i >= 2 else ''
            if prev_line and re.match(r'^[A-Za-z()（）]+$', prev_line) and prev2:
                fund_name = prev2 + prev_line

            if fund_name not in ['定投', '买入', '卖出', '转换']:
                funds.append({
                    'fund_name': fund_name,
                    'current_value': market_val,
                    'current_profit': profit,
                })
            i += 1
            continue

        # 检测是否是纯数字金额行：7,333.71 或 2493.93
        amount_match = re.match(r'^(\d{1,3}(?:,\d{3})*\.?\d{1,2})$', line)
        if amount_match:
            market_val = float(amount_match.group(1).replace(',', ''))

            # 找基金名（前几行中包含中文且像基金名的行）
            fund_name = ''
            for j in range(i - 1, max(i - 4, -1), -1):
                prev = clean_lines[j]
                # 必须包含中文，不能是纯数字，不能太短
                if (re.search(r'[\u4e00-\u9fff]', prev) and
                    not re.match(r'^[+\-]?\d', prev) and
                    len(prev) >= 4 and
                    prev not in ['定投', '买入', '卖出', '转换']):
                    fund_name = prev
                    break

            # 找收益（下一行带 +/- 的）
            profit = 0.0
            profit_rate = None
            for j in range(i + 1, min(i + 3, len(clean_lines))):
                next_line = clean_lines[j]
                sign = re.search(r'^([+\-])\s*(\d{1,3}(?:,\d{3})*\.?\d{1,2})$', next_line)
                if sign:
                    profit = float(sign.group(2).replace(',', ''))
                    if sign.group(1) == '-':
                        profit = -profit
                    break
                pct = re.search(r'^([+\-]?\d+\.?\d*)%$', next_line)
                if pct:
                    profit_rate = float(pct.group(1))

            if fund_name and market_val > 0:
                funds.append({
                    'fund_name': fund_name.strip(),
                    'current_value': market_val,
                    'current_profit': profit,
                    'profit_rate': profit_rate,
                })

        i += 1

    result: dict = {}
    if funds:
        result['fund_name'] = funds[0].get('fund_name', '')
        result['current_value'] = funds[0].get('current_value', 0)
        result['current_profit'] = funds[0].get('current_profit', 0)
    result['all_funds'] = funds
    return result


async def enrich_funds_with_codes(funds: list[dict]) -> list[dict]:
    """为识别的基金自动匹配基金代码"""
    if not funds:
        return funds
    from app.services.fund_crawler import search_funds
    for f in funds:
        name = f.get("fund_name", "")
        if not name:
            continue
        # 提取关键词搜索
        keyword = name.split("(")[0].split("（")[0].strip()
        if len(keyword) < 3:
            keyword = name
        results = await search_funds(keyword)
        if results:
            f["fund_code"] = results[0]["code"]
    return funds


@router.post("/parse")
async def parse_ocr(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
):
    """上传持仓截图，OCR 提取基金信息（支持支付宝/天天基金/微信）"""
    if not file.content_type or not file.content_type.startswith("image/"):
        return JSONResponse({"error": "请上传图片文件"}, status_code=400)

    file_bytes = await file.read()
    if len(file_bytes) > 10 * 1024 * 1024:
        return JSONResponse({"error": "图片过大（最大 10MB）"}, status_code=400)

    # 直接调 tesseract CLI
    text = _ocr_tesseract_cli(file_bytes)

    if not text:
        return JSONResponse({
            "error": "OCR 引擎未就绪。easyocr 已安装但可能需要预热。请重试一次，或手动录入。",
            "fund_code": "",
        }, status_code=200)

    # 解析
    info = parse_fund_from_text(text)
    info["raw_text"] = text[:300]
    # 自动匹配基金代码
    if info.get("all_funds"):
        info["all_funds"] = await enrich_funds_with_codes(info["all_funds"])

    return JSONResponse(info)


@router.post("/parse-text")
async def parse_text(
    body: dict,
    current_user: User = Depends(get_current_user),
):
    """直接粘贴 OCR 文字（如微信/系统 OCR 结果）"""
    text = body.get("text", "")
    if not text:
        return JSONResponse({"error": "请提供 OCR 文字"}, status_code=400)
    info = parse_fund_from_text(text)
    info["raw_text"] = text[:300]
    if info.get("all_funds"):
        info["all_funds"] = await enrich_funds_with_codes(info["all_funds"])
    return JSONResponse(info)
