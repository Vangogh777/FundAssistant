from pydantic import BaseModel
from typing import Optional


# AI Analysis Schemas
class AIAnalysisRequest(BaseModel):
    fund_code: str
    model: str = "deepseek"                     # openai / deepseek / claude
    periods: list[str] = ["1d", "3d", "5d"]     # 预测周期
    include_sentiment: bool = True               # 是否包含消息面分析
    include_technical: bool = True               # 是否包含技术面分析


class PeriodPrediction(BaseModel):
    period: str                                  # 1d / 3d / 5d / 7d
    predicted_change_pct: float                  # 预测涨跌幅 %
    confidence_score: float                      # 可信度 0-100
    confidence_reason: str                       # 可信度依据
    key_factors: list[str]                       # 关键影响因素
    up_probability: float = 0.0                  # 上涨概率 %


class BacktestResult(BaseModel):
    fund_code: str
    fund_name: str
    period_start: str
    period_end: str
    initial_investment: float                    # 初始投资金额
    final_value: float                           # 最终价值
    total_return_pct: float                      # 总收益率 %
    annualized_return_pct: float                 # 年化收益率 %
    max_drawdown: float                          # 最大回撤 %
    sharpe_ratio: float                          # 夏普比率
    volatility: float                            # 波动率 %
    win_rate: float                              # 胜率 %


class AIAnalysisResponse(BaseModel):
    fund_code: str
    fund_name: str
    model_used: str
    overall_assessment: str                       # 综合评估
    market_sentiment: str = ""                    # 市场情绪分析
    predictions: list[PeriodPrediction]            # 各周期预测
    backtest: Optional[BacktestResult] = None     # 回测结果
    risk_warning: str = ""                        # 风险提示
    advice: str = ""                              # 操作建议
