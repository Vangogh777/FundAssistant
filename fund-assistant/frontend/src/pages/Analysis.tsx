import React, { useState, useEffect } from 'react';
import {
  Typography, Card, Row, Col, Select, Button, Input, Table, Statistic,
  Progress, Tag, Spin, Space, Tabs, Tooltip, Divider, Empty
} from 'antd';
import {
  RobotOutlined, ThunderboltOutlined, BarChartOutlined,
  InfoCircleOutlined, LineChartOutlined
} from '@ant-design/icons';
import { fundApi } from '@/api/fund';
import { useAuth } from '@/hooks/useAuth';
import client from '@/api/client';
import { message } from 'antd';

const { Title, Text, Paragraph } = Typography;

interface Prediction {
  period: string; predicted_change_pct: number; confidence_score: number;
  confidence_reason: string; key_factors: string[]; up_probability: number;
}

interface TechIndicators {
  momentum_5d: number; volatility_annual: number; sharpe_ratio: number;
  max_drawdown: number; win_rate: number; expected_annual_return: number;
  avg_daily_return: number; recent_avg_daily_return: number;
}

interface ModelProvider { provider: string; label: string; models: { key: string; label: string }[]; }

// ===== 快速预测（无需 AI Key）=====
const QuickPredict: React.FC = () => {
  const [code, setCode] = useState('');
  const [nameSearch, setNameSearch] = useState('');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<any>(null);
  const [myFunds, setMyFunds] = useState<{ code: string; name: string }[]>([]);

  // 加载持仓基金列表
  useEffect(() => {
    fundApi.getPortfolios().then(r => {
      const funds = (r.data || []).map((p: any) => ({ code: p.fund_code, name: p.fund_name || p.fund_code }));
      setMyFunds(funds);
    }).catch(() => {});
  }, []);

  const run = async (fundCode?: string) => {
    const c = fundCode || code;
    if (!c) return;
    setLoading(true);
    try {
      const res = await client.get(`/analysis/predict/${c}?days=120`);
      setResult(res.data);
    } catch (e: any) {
      setResult({ error: e?.response?.data?.detail || '预测失败' });
    } finally { setLoading(false); }
  };

  // 名称搜索
  const handleNameSearch = async (kw: string) => {
    setNameSearch(kw);
    if (kw.length >= 2) {
      try {
        const res = await fundApi.search(kw);
        const funds = (res.data || []).map((f: any) => ({ code: f.code, name: f.name }));
        // 合并到持仓列表显示（去重）
        setMyFunds(prev => {
          const existing = new Set(prev.map(x => x.code));
          const newFunds = funds.filter((f: any) => !existing.has(f.code));
          return [...prev, ...newFunds];
        });
      } catch {}
    }
  };

  // 选基金即预测
  const handleSelect = (val: string) => {
    setCode(val);
    run(val);
  };

  return (
    <div>
      <Card style={{ marginBottom: 16 }}>
        <Space wrap style={{ width: '100%' }}>
          <Select
            showSearch
            value={code || undefined}
            placeholder="选择持仓基金 或 搜索基金名称"
            onChange={handleSelect}
            onSearch={handleNameSearch}
            filterOption={false}
            style={{ minWidth: 280, maxWidth: 400 }}
            options={myFunds.map(f => ({
              value: f.code,
              label: <span>{f.name} <Text type="secondary" style={{ fontSize: 11 }}>{f.code}</Text></span>,
            }))}
          />
          <Input placeholder="或输入代码" value={code} onChange={e => setCode(e.target.value)}
            onPressEnter={() => run()} style={{ width: 120 }} />
          <Button type="primary" onClick={() => run()} loading={loading} icon={<ThunderboltOutlined />}>
            预测
          </Button>
          <Text type="secondary">基于技术面分析，无需 API Key</Text>
        </Space>
      </Card>

      {result?.error && <Text type="danger">{result.error}</Text>}
      {loading && <Spin size="large" style={{ display: 'block', margin: '40px auto' }} />}

      {result?.predictions && (
        <>
          {/* 技术指标卡片 */}
          <Row gutter={[16, 16]} style={{ marginBottom: 16 }}>
            {[
              { label: '5日动量', value: result.technical_indicators?.momentum_5d, unit: '%', color: true },
              { label: '年化波动率', value: result.technical_indicators?.volatility_annual, unit: '%' },
              { label: '夏普比率', value: result.technical_indicators?.sharpe_ratio, precision: 2 },
              { label: '最大回撤', value: result.technical_indicators?.max_drawdown, unit: '%', danger: true },
              { label: '历史胜率', value: result.technical_indicators?.win_rate, unit: '%' },
              { label: '预期年化收益', value: result.technical_indicators?.expected_annual_return, unit: '%', color: true },
            ].map(item => (
              <Col xs={12} sm={8} md={4} key={item.label}>
                <Card size="small" hoverable>
                  <Statistic title={item.label}
                    value={item.value ?? '--'}
                    precision={item.precision ?? 1}
                    suffix={item.unit || ''}
                    valueStyle={{
                      fontSize: 22,
                      color: item.color ? (Number(item.value || 0) >= 0 ? '#ff4d4f' : '#52c41a')
                        : item.danger ? '#ff4d4f' : undefined,
                    }}
                  />
                </Card>
              </Col>
            ))}
          </Row>

          {/* 预测表格 */}
          <Card title="🔮 1-7 天涨跌预测" style={{ marginBottom: 16 }}>
            <Table dataSource={result.predictions} rowKey="period" pagination={false} size="middle"
              columns={[
                { title: '周期', dataIndex: 'period', key: 'p', width: 80, render: (v: string) => <Tag color="blue">{v.replace('d', '天')}</Tag> },
                {
                  title: '预测涨跌', dataIndex: 'predicted_change_pct', key: 'pred', width: 110,
                  render: (v: number) => <Text strong style={{ color: v >= 0 ? '#ff4d4f' : '#52c41a', fontSize: 20 }}>{v >= 0 ? '+' : ''}{v.toFixed(2)}%</Text>,
                },
                {
                  title: '可信度', dataIndex: 'confidence_score', key: 'conf', width: 140,
                  render: (v: number) => <Progress percent={v} size="small" strokeColor={v >= 60 ? '#1677ff' : v >= 40 ? '#faad14' : '#ff4d4f'} format={() => `${v}%`} />,
                },
                {
                  title: '上涨概率', dataIndex: 'up_probability', key: 'up', width: 100,
                  render: (v: number) => <Text strong style={{ color: v >= 50 ? '#ff4d4f' : '#52c41a', fontSize: 18 }}>{v}%</Text>,
                },
                {
                  title: '关键因素', dataIndex: 'key_factors', key: 'f',
                  render: (items: string[]) => (
                    <ul style={{ margin: 0, paddingLeft: 16 }}>
                      {items.map((f, i) => <li key={i}><Text style={{ fontSize: 12 }}>{f}</Text></li>)}
                    </ul>
                  ),
                },
              ]} />
          </Card>

          <Card>
            <Text strong style={{ display: 'block', marginBottom: 8 }}>📋 {result.fund_name} 各周期详细解读</Text>
            {result.predictions.map((p: Prediction) => (
              <Paragraph key={p.period} style={{ marginBottom: 8 }}>
                <Tag>{p.period.replace('d', '天')}</Tag>
                预计涨跌 <Text strong style={{ color: p.predicted_change_pct >= 0 ? '#ff4d4f' : '#52c41a' }}>{p.predicted_change_pct >= 0 ? '+' : ''}{p.predicted_change_pct}%</Text>，
                可信度 {p.confidence_score}%，上涨概率 {p.up_probability}%。
                {p.confidence_reason}
              </Paragraph>
            ))}
          </Card>
        </>
      )}
    </div>
  );
};

// ===== AI 深度分析（需 Key）=====
const AIAnalysis: React.FC = () => {
  const { user } = useAuth();
  const [code, setCode] = useState('');
  const [model, setModel] = useState('deepseek-v4-flash');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<any>(null);
  const [providers, setProviders] = useState<ModelProvider[]>([]);
  const [myFunds, setMyFunds] = useState<{ code: string; name: string }[]>([]);

  useEffect(() => {
    client.get('/analysis/models').then(r => setProviders(r.data)).catch(() => {});
    fundApi.getPortfolios().then(r => {
      setMyFunds((r.data || []).map((p: any) => ({ code: p.fund_code, name: p.fund_name || p.fund_code })));
    }).catch(() => {});
  }, []);

  const currentProvider = providers.find(p => p.models.some(m => m.key === model));
  const hasKey = currentProvider && user?.api_keys?.[currentProvider.provider];

  const run = async (fundCode?: string) => {
    const c = fundCode || code;
    if (!c) return;
    setLoading(true);
    try {
      const res = await fundApi.analyzeFund({ fund_code: c, model, periods: ['1d', '3d', '5d', '7d'], include_sentiment: true, include_technical: true });
      setResult(res.data);
    } catch (e: any) { setResult({ error: e?.response?.data?.detail || '分析失败' }); }
    finally { setLoading(false); }
  };

  return (
    <div>
      <Card style={{ marginBottom: 16 }}>
        <Space wrap style={{ width: '100%' }}>
          <Select value={model} onChange={setModel} style={{ width: 260 }}
            options={providers.flatMap(p => p.models.map(m => ({
              value: m.key,
              label: <Space><Text type="secondary" style={{ fontSize: 11 }}>{p.label}</Text><span>{m.label}</span></Space>,
            })))} />
          <Select
            showSearch
            value={code || undefined}
            placeholder="持仓基金 / 搜索名称"
            onChange={(val) => { setCode(val); run(val); }}
            filterOption={false}
            style={{ minWidth: 220 }}
            options={myFunds.map(f => ({
              value: f.code,
              label: <span>{f.name} <Text type="secondary" style={{ fontSize: 11 }}>{f.code}</Text></span>,
            }))}
          />
          <Input placeholder="或输入代码" value={code} onChange={e => setCode(e.target.value)}
            onPressEnter={() => run()} style={{ width: 120 }} />
          <Button type="primary" onClick={() => run()} loading={loading} icon={<RobotOutlined />}>
            分析
          </Button>
          {!hasKey && (
            <Text type="secondary">⚠️ 未配置 {currentProvider?.label} Key</Text>
          )}
        </Space>
      </Card>

      {result?.error && <Text type="danger">{result.error}</Text>}
      {loading && <Spin size="large" style={{ display: 'block', margin: '40px auto' }} />}

      {result?.overall_assessment && (
        <>
          <Row gutter={[16, 16]} style={{ marginBottom: 16 }}>
            <Col xs={24} md={12}><Card title="📋 综合评估"><Paragraph>{result.overall_assessment}</Paragraph>{result.is_ai_fallback && <Tag color="orange">本地技术分析</Tag>}</Card></Col>
            <Col xs={24} md={12}><Card title="💡 操作建议"><Paragraph>{result.advice}</Paragraph></Card></Col>
          </Row>
          <Row gutter={[16, 16]} style={{ marginBottom: 16 }}>
            <Col xs={24} md={12}><Card title="📰 市场情绪"><Paragraph>{result.market_sentiment || '无'}</Paragraph></Card></Col>
            <Col xs={24} md={12}><Card title="⚠️ 风险提示"><Paragraph>{result.risk_warning || '无'}</Paragraph></Card></Col>
          </Row>

          {result.technical_indicators && (
            <Row gutter={[16, 16]} style={{ marginBottom: 16 }}>
              {[
                { label: '5日动量', value: result.technical_indicators.momentum_5d, unit: '%', color: true },
                { label: '波动率', value: result.technical_indicators.volatility_annual, unit: '%' },
                { label: '夏普', value: result.technical_indicators.sharpe_ratio, precision: 2 },
                { label: '回撤', value: result.technical_indicators.max_drawdown, unit: '%', danger: true },
                { label: '胜率', value: result.technical_indicators.win_rate, unit: '%' },
                { label: '预期年化', value: result.technical_indicators.expected_annual_return, unit: '%', color: true },
              ].map(item => (
                <Col xs={12} sm={8} md={4} key={item.label}>
                  <Card size="small"><Statistic title={item.label} value={item.value ?? '--'} precision={item.precision ?? 1} suffix={item.unit || ''}
                    valueStyle={{ fontSize: 20, color: item.color ? (Number(item.value || 0) >= 0 ? '#ff4d4f' : '#52c41a') : item.danger ? '#ff4d4f' : undefined }} /></Card>
                </Col>
              ))}
            </Row>
          )}

          {result.predictions?.length > 0 && (
            <Card title="🔮 涨跌预测" style={{ marginBottom: 16 }}>
              <Table dataSource={result.predictions} rowKey="period" pagination={false} size="small"
                columns={[
                  { title: '周期', dataIndex: 'period', render: (v: string) => <Tag>{v.replace('d', '天')}</Tag> },
                  { title: '预测', dataIndex: 'predicted_change_pct', render: (v: number) => <Text strong style={{ color: v >= 0 ? '#ff4d4f' : '#52c41a', fontSize: 16 }}>{v >= 0 ? '+' : ''}{v.toFixed(2)}%</Text> },
                  { title: '可信度', dataIndex: 'confidence_score', render: (v: number) => <Progress percent={v} size="small" /> },
                  { title: '上涨概率', dataIndex: 'up_probability', render: (v: number) => `${v}%` },
                ]} />
            </Card>
          )}
        </>
      )}
    </div>
  );
};

// ===== 持仓基金分析 =====
const PortfolioReport: React.FC = () => {
  const [loading, setLoading] = useState(false);
  const [report, setReport] = useState<any>(null);

  useEffect(() => { loadReport(); }, []);

  const loadReport = async () => {
    setLoading(true);
    try {
      const res = await client.get('/analysis/portfolio-report');
      setReport(res.data);
    } catch { /* */ }
    finally { setLoading(false); }
  };

  const funds = report?.funds || [];
  const stocks = report?.top_stocks || [];

  return (
    <Spin spinning={loading}>
      {!report ? <Card><Text type="secondary">加载中...</Text></Card> : (
        <>
          {/* 组合概览 */}
          <Row gutter={[12, 12]} style={{ marginBottom: 16 }}>
            <Col xs={12} sm={6}><Card size="small"><Statistic title="持仓基金" value={funds.length} suffix="只" /></Card></Col>
            <Col xs={12} sm={6}><Card size="small"><Statistic title="穿透股票" value={stocks.length} suffix="只" /></Card></Col>
            <Col xs={12} sm={6}><Card size="small"><Statistic title="股票仓位" value={report?.sector_allocation?.stock || 0} suffix="%" /></Card></Col>
            <Col xs={12} sm={6}><Card size="small"><Statistic title="债券仓位" value={report?.sector_allocation?.bond || 0} suffix="%" /></Card></Col>
          </Row>

          {/* 持仓基金 */}
          <Card title="📋 持仓基金" size="small" style={{ marginBottom: 12 }}>
            <Table dataSource={funds} rowKey="fund_code" pagination={false} size="small"
              columns={[
                { title: '基金', dataIndex: 'fund_name', width: 160, render: (n:string,r:any) => <div><Text strong>{n}</Text><br /><Text type="secondary" style={{fontSize:11}}>{r.fund_code} | {r.fund_type}</Text></div> },
                { title: '市值', dataIndex: 'market_value', render: (v:number) => `¥${v?.toFixed(0)}` },
                { title: '盈亏', render: (_:any,r:any) => <Text strong style={{color:r.profit_pct>=0?'#ff4d4f':'#52c41a'}}>{r.profit_pct>=0?'+':''}{r.profit_pct}%</Text> },
                { title: '重仓股数', dataIndex: 'holdings_count' },
              ]} />
          </Card>

          {/* 穿透重仓股 */}
          <Card title="🔍 穿透十大重仓股" size="small" style={{ marginBottom: 12 }}>
            <Table dataSource={stocks} rowKey="code" pagination={false} size="small"
              columns={[
                { title: '股票', dataIndex: 'name', width: 120, render: (n:string,r:any) => <div><Text strong>{n||'--'}</Text><br /><Text type="secondary" style={{fontSize:11}}>{r.code}</Text></div> },
                { title: '最新价', dataIndex: 'price', render: (v:number) => v>0?`¥${v.toFixed(2)}`:'--' },
                { title: '涨跌', dataIndex: 'change_pct', render: (v:number) => v!==undefined?<Text style={{color:v>=0?'#ff4d4f':'#52c41a'}}>{v>=0?'+':''}{v?.toFixed(2)}%</Text>:'--' },
                { title: '综合权重', dataIndex: 'total_weight', render: (v:number) => v?.toFixed(2) },
                { title: '来源基金', dataIndex: 'funds', render: (fs:any[]) => fs?.map((f:any) => <Tag key={f.fund_code} style={{fontSize:10}}>{f.fund_name?.slice(0,8)}</Tag>) },
              ]} />
          </Card>

          {/* AI 建议格式预览 */}
          <Card title="🤖 AI 交易建议（需配置 Key）" size="small">
            <Text type="secondary">
              配置 DeepSeek/OpenAI Key 后，AI 将按以下格式输出：
            </Text>
            <pre style={{ padding: 12, borderRadius: 6, fontSize: 12, marginTop: 8, border: '1px solid var(--border-color, #e8ecf1)' }}>
{`【组合总评】
...

【风险等级】
高/中/低风险

【加仓建议】
- 基金(代码)：可加仓/暂不加仓，理由

【减仓/清仓建议】
- 基金(代码)：减仓/清仓/持有，理由

【补仓建议】
- 基金(代码)：可补仓/不建议，理由

【后市展望】
...`}
            </pre>
            <Button icon={<RobotOutlined />} style={{ marginTop: 12 }}
              onClick={() => {
                const prompt = report?.ai_prompt || '';
                navigator.clipboard.writeText(prompt);
                message.success('AI 提示已复制，可粘贴到 AI 工具中使用');
              }}>
              复制分析 Prompt
            </Button>
          </Card>
        </>
      )}
    </Spin>
  );
};

// ===== 主页 =====
const Analysis: React.FC = () => {
  return (
    <div>
      <Title level={3}>🤖 AI 智能分析</Title>
      <Tabs defaultActiveKey="portfolio"
        items={[
          {
            key: 'portfolio',
            label: <span>📊 持仓分析</span>,
            children: <PortfolioReport />,
          },
          {
            key: 'predict',
            label: <span><LineChartOutlined /> 快速预测</span>,
            children: <QuickPredict />,
          },
          {
            key: 'ai',
            label: <span><RobotOutlined /> AI 深度分析</span>,
            children: <AIAnalysis />,
          },
        ]} />
    </div>
  );
};

export default Analysis;
