"""
OCR 图片识别 — 支持支付宝/天天基金等持仓截图
直接用 tesseract CLI 调用，绕过 Python 依赖冲突
"""
import re
import io
import subprocess
import tempfile
import os
import asyncio
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

# 支付宝特有标签映射
ALIPAY_LABELS = {
    '持有收益': 'profit',
    '昨日收益': 'yesterday_profit',
    '持有金额': 'market_value',
    '收益率': 'profit_rate',
    '持有份额': 'shares',
    '最新净值': 'nav',
}

# 基金名称常见英文后缀（用于名称提取）
FUND_SUFFIXES = ['A', 'C', 'E', 'I', 'R', 'QDII', 'FOF', 'LOF', 'ETF', 'H']

# OCR 常见错误映射（0/O 混淆等）
OCR_CORRECTIONS = {
    'O': '0', 'o': '0',
    'l': '1', 'I': '1', 'i': '1',
    'S': '5', 's': '5',
    'B': '8',
    'Z': '2', 'z': '2',
}


def _correct_ocr_number(text: str) -> str:
    """修正 OCR 识别数字时的常见错误（0/O 混淆等）"""
    result = []
    for i, ch in enumerate(text):
        # 只在数字上下文中修正
        if ch in OCR_CORRECTIONS:
            # 检查前后字符是否为数字
            prev_is_digit = i > 0 and text[i-1].isdigit()
            next_is_digit = i < len(text) - 1 and text[i+1].isdigit()
            if prev_is_digit or next_is_digit:
                result.append(OCR_CORRECTIONS[ch])
                continue
        result.append(ch)
    return ''.join(result)


def _parse_amount(text: str) -> float | None:
    """解析金额字符串，处理 OCR 错误"""
    text = _correct_ocr_number(text)
    # 移除货币符号和空格
    text = re.sub(r'[¥￥\s]', '', text)
    # 移除逗号
    text = text.replace(',', '')
    try:
        return float(text)
    except ValueError:
        return None


def _extract_fund_name(lines: list[str], start_idx: int, direction: int = -1) -> str:
    """
    从指定位置向前或向后提取基金名称
    处理带括号、带英文后缀的情况
    """
    fund_name_parts = []
    search_range = range(start_idx + direction, max(-1, start_idx - 5), direction)

    for j in search_range:
        if j < 0 or j >= len(lines):
            continue
        line = lines[j].strip()

        # 跳过金额、收益等数字行
        if re.match(r'^[+\-]?\d{1,3}(?:,\d{3})*\.?\d{1,2}%?$', line):
            continue
        if re.match(r'^[¥￥]?\s*[+\-]?\d', line):
            continue
        if re.match(r'^[+\-]?\d+\.?\d*%$', line):
            continue

        # 跳过标签行
        if line in ['定投', '买入', '卖出', '转换', '持有', '基金']:
            continue
        if any(label in line for label in ['持有收益', '昨日收益', '持有金额', '收益率']):
            continue

        # 必须包含中文（基金名核心）
        if re.search(r'[一-鿿]', line):
            # 检查是否是基金名（包含关键词或长度足够）
            fund_keywords = ['基金', '混合', '股票', '债券', '指数', '货币', '理财',
                            '配置', '成长', '价值', '精选', '稳健', '进取', '灵活']
            is_likely_fund = any(kw in line for kw in fund_keywords) or len(line) >= 4

            if is_likely_fund:
                fund_name_parts.insert(0, line)
                break

        # 检查是否是英文后缀（A/C/QDII 等）
        elif re.match(r'^[A-Za-z()（）]+$', line) and len(line) <= 10:
            fund_name_parts.insert(0, line)
            # 继续向前找主名称

    return ''.join(fund_name_parts).strip()


def _normalize_fund_name(name: str) -> str:
    """规范化基金名称"""
    # 统一括号
    name = name.replace('（', '(').replace('）', ')')
    # 去除多余空格
    name = ' '.join(name.split())
    # 处理粘连的后缀（如 "XXX混合A" → 保持原样）
    return name


def _detect_alipay_block(lines: list[str], start_idx: int) -> dict | None:
    """
    检测支付宝特有的格式块
    格式：基金名 → 持有金额 → 持有收益 → 收益率% → 昨日收益（可选）
    """
    if start_idx >= len(lines) - 1:
        return None

    result = {}

    # 查找标签和对应的值
    i = start_idx
    while i < len(lines) and i < start_idx + 8:
        line = lines[i].strip()

        # 检测标签行
        for label, key in ALIPAY_LABELS.items():
            if label in line:
                # 尝试从同一行提取值
                value_match = re.search(r'[¥￥]?\s*([+\-]?\d{1,3}(?:,\d{3})*\.?\d{1,2})%?', line)
                if value_match:
                    val = _parse_amount(value_match.group(1))
                    if val is not None:
                        result[key] = val
                else:
                    # 检查下一行
                    if i + 1 < len(lines):
                        next_line = lines[i + 1].strip()
                        next_match = re.match(r'^[¥￥]?\s*([+\-]?\d{1,3}(?:,\d{3})*\.?\d{1,2})%?', next_line)
                        if next_match:
                            val = _parse_amount(next_match.group(1))
                            if val is not None:
                                result[key] = val
                                i += 1  # 跳过已处理的值行
                break
        i += 1

    # 提取基金名称（在块的开头查找）
    fund_name = _extract_fund_name(lines, start_idx, direction=-1)
    if fund_name:
        result['fund_name'] = _normalize_fund_name(fund_name)

    return result if result else None


def parse_fund_from_text(text: str) -> dict:
    """从 OCR 文本提取基金持仓信息，适配支付宝/天天基金/微信截图"""
    lines = [l.strip() for l in text.split('\n') if l.strip()]

    # 第一步：过滤垃圾行
    skip_words = ['去看看', '基金市场', '机会', '自选', '公告', '产品提醒',
                  '财富号', '存储巨头', '营收净利', '定投', '持有收益排序',
                  '名称', '金额/昨日收益', '持有收益/率',
                  '我的持有', '去看看', '金选', '指数基金',
                  '基金详情', '交易记录', '规则说明', '费率']
    # 整行匹配的短标签（不做子串匹配，避免误杀基金名）
    exact_skip = {'全部', '黄金', '全球', '偏股', '偏债', '指数', '基金', '持有', 'H', '固定'}
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

        # === 支付宝特有标签检测 ===
        has_alipay_label = any(label in line for label in ['持有收益', '昨日收益', '持有金额'])
        if has_alipay_label:
            block = _detect_alipay_block(clean_lines, i)
            if block and block.get('fund_name'):
                fund = {
                    'fund_name': block.get('fund_name', ''),
                    'current_value': block.get('market_value', 0),
                    'current_profit': block.get('profit', 0),
                    'profit_rate': block.get('profit_rate'),
                    'yesterday_profit': block.get('yesterday_profit', 0),
                }
                # 避免重复添加
                if not any(f['fund_name'] == fund['fund_name'] for f in funds):
                    funds.append(fund)
                i += 1
                continue

        # 检测行内是否嵌有金额（基金名+金额粘在一起，如"华夏移动互联灵活配置混合6,633.29"）
        inline_match = re.match(r'^([一-鿿A-Za-z()（）\s]+?)\s*(\d{1,3}(?:,\d{3})*\.?\d{1,2})$', line)
        if inline_match and len(inline_match.group(1).strip()) >= 4:
            fund_name = inline_match.group(1).strip()
            market_val = _parse_amount(inline_match.group(2))
            if market_val is None:
                market_val = 0.0

            # 找收益和收益率
            profit = 0.0
            profit_rate = None
            yesterday_profit = 0.0
            for j in range(i + 1, min(i + 4, len(clean_lines))):
                next_line = clean_lines[j]

                # 匹配收益（带符号的金额）
                sign_match = re.match(r'^([+\-])\s*(\d{1,3}(?:,\d{3})*\.?\d{1,2})$', next_line)
                if sign_match:
                    val = _parse_amount(sign_match.group(2))
                    if val is not None:
                        profit = val if sign_match.group(1) == '+' else -val
                    continue

                # 匹配收益率
                pct_match = re.match(r'^([+\-]?\d+\.?\d*)\s*%$', next_line)
                if pct_match:
                    profit_rate = float(pct_match.group(1))
                    continue

                # 匹配昨日收益标签
                if '昨日收益' in next_line:
                    val_match = re.search(r'([+\-]?\d{1,3}(?:,\d{3})*\.?\d{1,2})', next_line)
                    if val_match:
                        yesterday_profit = _parse_amount(val_match.group(1)) or 0.0

            # 如果前一行是纯英文/符号（如 "QDII)A"），拼到基金名上
            if i >= 1:
                prev_line = clean_lines[i - 1]
                prev2 = clean_lines[i - 2] if i >= 2 else ''
                if re.match(r'^[A-Za-z()（）]+$', prev_line) and prev2:
                    fund_name = prev2 + prev_line

            fund_name = _normalize_fund_name(fund_name)
            if fund_name not in ['定投', '买入', '卖出', '转换']:
                funds.append({
                    'fund_name': fund_name,
                    'current_value': market_val,
                    'current_profit': profit,
                    'profit_rate': profit_rate,
                    'yesterday_profit': yesterday_profit,
                })
            i += 1
            continue

        # 检测是否是纯数字金额行：7,333.71 或 2493.93
        amount_match = re.match(r'^(\d{1,3}(?:,\d{3})*\.?\d{1,2})$', line)
        if amount_match:
            market_val = _parse_amount(amount_match.group(1))
            if market_val is None:
                market_val = 0.0

            # 找基金名（前几行中包含中文且像基金名的行）
            fund_name = _extract_fund_name(clean_lines, i, direction=-1)
            fund_name = _normalize_fund_name(fund_name)

            # 找收益、收益率、昨日收益（下一行带 +/- 的）
            profit = 0.0
            profit_rate = None
            yesterday_profit = 0.0
            for j in range(i + 1, min(i + 4, len(clean_lines))):
                next_line = clean_lines[j]

                # 匹配收益（带符号的金额）
                sign_match = re.match(r'^([+\-])\s*(\d{1,3}(?:,\d{3})*\.?\d{1,2})$', next_line)
                if sign_match:
                    val = _parse_amount(sign_match.group(2))
                    if val is not None:
                        profit = val if sign_match.group(1) == '+' else -val
                    continue

                # 匹配收益率
                pct_match = re.match(r'^([+\-]?\d+\.?\d*)\s*%$', next_line)
                if pct_match:
                    profit_rate = float(pct_match.group(1))
                    continue

                # 匹配昨日收益
                if '昨日收益' in next_line:
                    val_match = re.search(r'([+\-]?\d{1,3}(?:,\d{3})*\.?\d{1,2})', next_line)
                    if val_match:
                        yesterday_profit = _parse_amount(val_match.group(1)) or 0.0

            if fund_name and market_val > 0:
                funds.append({
                    'fund_name': fund_name.strip(),
                    'current_value': market_val,
                    'current_profit': profit,
                    'profit_rate': profit_rate,
                    'yesterday_profit': yesterday_profit,
                })

        i += 1

    result: dict = {}
    if funds:
        result['fund_name'] = funds[0].get('fund_name', '')
        result['current_value'] = funds[0].get('current_value', 0)
        result['current_profit'] = funds[0].get('current_profit', 0)
        result['profit_rate'] = funds[0].get('profit_rate')
        result['yesterday_profit'] = funds[0].get('yesterday_profit', 0)
    result['all_funds'] = funds
    return result


async def enrich_funds_with_codes(funds: list[dict]) -> list[dict]:
    """为识别的基金自动匹配基金代码（多轮模糊搜索）"""
    if not funds:
        return funds
    from app.services.fund_crawler import search_funds
    import asyncio

    async def match_one(name: str) -> str:
        # 第1轮：全名去括号搜索（并清理OCR错字）
        kw = name.replace("(", "").replace(")", "").replace("（", "").replace("）", "")
        kw = kw.replace("QDII", "QDII").replace("QDII", "QDII")
        if len(kw) >= 3:
            r = await search_funds(kw)
            if r:
                return r[0]["code"]

        # 第2轮：取前4-6个字分段搜（模糊）
        for length in [6, 5, 4]:
            if len(kw) >= length:
                r = await search_funds(kw[:length])
                if r:
                    return r[0]["code"]

        return ""

    tasks = [match_one(f.get("fund_name", "")) for f in funds]
    codes = await asyncio.gather(*tasks)
    for f, code in zip(funds, codes):
        if code:
            f["fund_code"] = code
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
