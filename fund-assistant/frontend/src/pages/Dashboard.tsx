import React, { useState, useEffect, useMemo } from 'react';
import { Row, Col, Card, Statistic, Table, Spin, Typography, Tabs, Segmented, Space } from 'antd';
import { RiseOutlined, FallOutlined, InfoCircleOutlined } from '@ant-design/icons';
import { fundApi } from '@/api/fund';
import { AreaChart, Area, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, ReferenceLine } from 'recharts';

const { Text, Title } = Typography;

interface PortfolioItem {
  id: number; fund_code: string; fund_name: string;
  shares: number; cost_per_share: number; total_cost: number;
  market_value: number; profit_loss: number; profit_loss_pct: number;
  estimated_nav: number; current_nav: number; buy_date: string;
}

type Period = '1m' | '3m' | '6m' | '1y' | 'all';

const Dashboard: React.FC = () => {
  const [portfolios, setPortfolios] = useState<PortfolioItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [analysis, setAnalysis] = useState<any>(null);
  const [period, setPeriod] = useState<Period>('all');

  useEffect(() => { loadData(); }, []);

  const loadData = async () => {
    setLoading(true);
    try { const res = await fundApi.getPortfolios(); setPortfolios(res.data); } catch {}
    try { const a = await fundApi.getPortfolioAnalysis(365); setAnalysis(a.data); } catch {}
    finally { setLoading(false); }
  };

  const totalCost = portfolios.reduce((s, p) => s + p.total_cost, 0);
  const totalMarket = portfolios.reduce((s, p) => s + p.market_value, 0);
  const totalPL = totalMarket - totalCost;
  const totalPLPct = totalCost > 0 ? (totalPL / totalCost) * 100 : 0;

  const todayPL = portfolios.reduce((s, p) => {
    if (!p.estimated_nav || !p.current_nav || p.current_nav === p.estimated_nav) return s;
    return s + p.shares * (p.estimated_nav - p.current_nav);
  }, 0);

  const todayPLPct = totalCost > 0 ? (todayPL / totalCost * 100) : 0;

  const fmtW = (v: number) => {
    const abs = Math.abs(v);
    if (abs >= 10000) return `${(v / 10000).toFixed(2)}万`;
    return `${v.toFixed(2)}`;
  };

  const curveData = useMemo(() => {
    if (!analysis?.curve) return [];
    const m: Record<Period, number> = { '1m': 30, '3m': 90, '6m': 180, '1y': 365, 'all': 9999 };
    const portfolio = analysis.curve.slice(-m[period]);
    const benchmark = analysis.benchmark || [];

    // 转百分比 + 合并沪深300
    const benchMap: Record<string, number> = {};
    benchmark.forEach((b: any) => { benchMap[b.date] = b.pct; });

    return portfolio.map((p: any) => ({
      date: p.date,
      profit: p.profit,                                    // 绝对金额
      myPct: analysis.total_invested > 0 ? (p.profit / analysis.total_invested * 100) : 0,  // 我的收益率
      hs300: benchMap[p.date] ?? null,                     // 沪深300收益率
    }));
  }, [analysis, period]);

  const monthlyBars = useMemo(() => {
    if (!analysis?.monthly) return [];
    return analysis.monthly.slice(-12).map((m: any) => ({ ...m, label: m.month?.slice(2) || m.month }));
  }, [analysis]);

  const dist = analysis?.distribution;

  const holdingsColumns = [
    {
      title: '基金', dataIndex: 'fund_name', key: 'name', width: 140,
      render: (n: string, r: PortfolioItem) => (
        <div><Text strong>{n || '--'}</Text><br /><Text type="secondary" style={{ fontSize: 11 }}>{r.fund_code}</Text></div>
      ),
    },
    {
      title: '本金', dataIndex: 'total_cost', key: 'cost', width: 90, sorter: (a: PortfolioItem, b: PortfolioItem) => a.total_cost - b.total_cost,
      render: (v: number) => `¥${v.toFixed(0)}`,
    },
    {
      title: '市值', dataIndex: 'market_value', key: 'market', width: 90, sorter: (a: PortfolioItem, b: PortfolioItem) => a.market_value - b.market_value,
      render: (v: number) => `¥${v.toFixed(0)}`,
    },
    {
      title: '今日收益', key: 'today', width: 100,
      render: (_: any, r: PortfolioItem) => {
        if (!r.estimated_nav || !r.current_nav || r.current_nav === r.estimated_nav) return <Text type="secondary">--</Text>;
        const pl = r.shares * (r.estimated_nav - r.current_nav);
        const pct = r.total_cost > 0 ? (pl / r.total_cost * 100) : 0;
        return (
          <div>
            <Text strong style={{ color: pl >= 0 ? '#ff4d4f' : '#52c41a', fontSize: 14 }}>{pl >= 0 ? '+' : ''}¥{pl.toFixed(2)}</Text>
            <br /><Text style={{ color: pl >= 0 ? '#ff4d4f' : '#52c41a', fontSize: 11 }}>{pct >= 0 ? '+' : ''}{pct.toFixed(2)}%</Text>
          </div>
        );
      },
    },
    {
      title: '持仓盈亏', key: 'pl', width: 110, sorter: (a: PortfolioItem, b: PortfolioItem) => a.profit_loss - b.profit_loss,
      defaultSortOrder: 'descend' as const,
      render: (_: any, r: PortfolioItem) => (
        <div>
          <Text strong style={{ color: r.profit_loss >= 0 ? '#ff4d4f' : '#52c41a', fontSize: 14 }}>{r.profit_loss >= 0 ? '+' : ''}¥{r.profit_loss.toFixed(2)}</Text>
          <br /><Text style={{ color: r.profit_loss_pct >= 0 ? '#ff4d4f' : '#52c41a', fontSize: 11 }}>{r.profit_loss_pct >= 0 ? '+' : ''}{r.profit_loss_pct.toFixed(2)}%</Text>
        </div>
      ),
    },
    { title: '买入日', dataIndex: 'buy_date', key: 'date', width: 90, responsive: ['md' as const] },
  ];

  return (
    <div>
      {/* 顶部资产卡片 — 仿基金App */}
      <Card style={{ marginBottom: 12, borderRadius: 12 }}>
        <Text type="secondary">总资产（元）</Text>
        <Title level={2} style={{ margin: '4px 0' }}>¥{totalMarket.toLocaleString('zh-CN', { minimumFractionDigits: 2 })}</Title>
        <Row gutter={16}>
          <Col span={8}>
            <Text type="secondary" style={{ fontSize: 12 }}>昨日收盘市值</Text>
            <br />
            <Text>¥{(totalMarket - todayPL).toFixed(2)}</Text>
          </Col>
          <Col span={8}>
            <Text type="secondary" style={{ fontSize: 12 }}>投入本金</Text>
            <br />
            <Text>¥{fmtW(totalCost)}</Text>
          </Col>
          <Col span={8}>
            <Text type="secondary" style={{ fontSize: 12 }}>持仓数量</Text>
            <br />
            <Text>{portfolios.length} 只</Text>
          </Col>
        </Row>
        <Row gutter={16} style={{ marginTop: 12 }}>
          <Col span={12}>
            <div style={{
              background: todayPL >= 0 ? 'rgba(255,77,79,0.08)' : 'rgba(82,196,26,0.08)',
              border: `1px solid ${todayPL >= 0 ? 'rgba(255,77,79,0.15)' : 'rgba(82,196,26,0.15)'}`,
              borderRadius: 10, padding: '12px 16px',
            }}>
              <Text type="secondary" style={{ fontSize: 12 }}>今日收益</Text>
              <br />
              <Text strong style={{ color: todayPL >= 0 ? '#ff4d4f' : '#52c41a', fontSize: 22 }}>
                {todayPL >= 0 ? '+' : ''}¥{todayPL.toFixed(2)}
              </Text>
              <Text style={{ color: todayPL >= 0 ? '#ff4d4f' : '#52c41a', fontSize: 13, marginLeft: 6 }}>
                {todayPLPct >= 0 ? '+' : ''}{todayPLPct.toFixed(2)}%
              </Text>
            </div>
          </Col>
          <Col span={12}>
            <div style={{
              background: totalPL >= 0 ? 'rgba(255,77,79,0.08)' : 'rgba(82,196,26,0.08)',
              border: `1px solid ${totalPL >= 0 ? 'rgba(255,77,79,0.15)' : 'rgba(82,196,26,0.15)'}`,
              borderRadius: 10, padding: '12px 16px',
            }}>
              <Text type="secondary" style={{ fontSize: 12 }}>持仓盈亏</Text>
              <br />
              <Text strong style={{ color: totalPL >= 0 ? '#ff4d4f' : '#52c41a', fontSize: 22 }}>
                {totalPL >= 0 ? '+' : ''}¥{fmtW(totalPL)}
              </Text>
              <Text style={{ color: totalPL >= 0 ? '#ff4d4f' : '#52c41a', fontSize: 13, marginLeft: 6 }}>
                {totalPLPct >= 0 ? '+' : ''}{totalPLPct.toFixed(2)}%
              </Text>
            </div>
          </Col>
        </Row>
      </Card>

      <Tabs defaultActiveKey="holdings" items={[
        {
          key: 'holdings',
          label: '📋 持仓',
          children: portfolios.length === 0
            ? <Card><Text type="secondary">暂无持仓，前往「持仓管理」添加</Text></Card>
            : <Card>
                <Table dataSource={portfolios} columns={holdingsColumns} rowKey="id"
                  pagination={false} size="middle" loading={loading}
                  scroll={{ x: 600 }}
                  locale={{ emptyText: '暂无持仓' }} />
              </Card>,
        },
        {
          key: 'chart',
          label: '📈 收益',
          children: !analysis?.curve ? (
            <Card><Text type="secondary">暂无数据（需有持仓且填写买入日期）</Text></Card>
          ) : (
            <>
              <div style={{ marginBottom: 12, display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 8 }}>
                {analysis.start_date && <Text type="secondary">📅 {analysis.start_date} ~ 至今</Text>}
                <Segmented value={period} onChange={(v) => setPeriod(v as Period)}
                  options={[
                    { value: '1m', label: '1月' },
                    { value: '3m', label: '3月' },
                    { value: '6m', label: '6月' },
                    { value: '1y', label: '1年' },
                    { value: 'all', label: '全部' },
                  ]} />
              </div>

              <Card style={{ marginBottom: 12 }}>
                <div style={{ display: 'flex', gap: 16, marginBottom: 8 }}>
                  <span><span style={{ display: 'inline-block', width: 12, height: 12, borderRadius: 2, background: '#ff4d4f', verticalAlign: 'middle', marginRight: 4 }} /> 我的持仓</span>
                  <span><span style={{ display: 'inline-block', width: 12, height: 12, borderRadius: 2, background: '#1677ff', verticalAlign: 'middle', marginRight: 4 }} /> 沪深300</span>
                </div>
                <ResponsiveContainer width="100%" height={260}>
                  <AreaChart data={curveData} margin={{ top: 5, right: 5, left: 0, bottom: 0 }}>
                    <defs>
                      <linearGradient id="pg" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="0%" stopColor="#ff4d4f" stopOpacity={0.35} />
                        <stop offset="100%" stopColor="#ff4d4f" stopOpacity={0} />
                      </linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" stroke="#1e3a5f22" />
                    <XAxis dataKey="date" tick={{ fontSize: 11 }} interval="preserveStartEnd" />
                    <YAxis yAxisId="left" tick={{ fontSize: 11 }} tickFormatter={v => `¥${v}`} />
                    <YAxis yAxisId="right" orientation="right" tick={{ fontSize: 11 }} tickFormatter={v => `${v}%`} />
                    <Tooltip formatter={(v: any, name: string) => {
                      if (name === 'profit') return [`¥${Number(v).toFixed(2)}`, '累计盈亏'];
                      if (name === 'myPct') return [`${Number(v).toFixed(2)}%`, '我的收益率'];
                      return [`${Number(v).toFixed(2)}%`, '沪深300'];
                    }} />
                    <ReferenceLine yAxisId="left" y={0} stroke="#52c41a" strokeDasharray="3 3" />
                    {/* 持仓累计盈亏（左轴，绝对金额） */}
                    <Area yAxisId="left" type="monotone" dataKey="profit" stroke="#ff4d4f" fill="url(#pg)" strokeWidth={2} dot={false} />
                    {/* 我的收益率（右轴） */}
                    <Area yAxisId="right" type="monotone" dataKey="myPct" stroke="#ff4d4f" strokeWidth={1.5} strokeDasharray="5 5" fill="none" dot={false} />
                    {/* 沪深300（右轴） */}
                    <Area yAxisId="right" type="monotone" dataKey="hs300" stroke="#1677ff" strokeWidth={2} fill="none" dot={false} connectNulls />
                  </AreaChart>
                </ResponsiveContainer>
              </Card>

              <Card title="📊 月度收益">
                <ResponsiveContainer width="100%" height={180}>
                  <BarChart data={monthlyBars}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#1e3a5f22" />
                    <XAxis dataKey="label" tick={{ fontSize: 11 }} />
                    <YAxis tick={{ fontSize: 11 }} tickFormatter={v => `¥${v}`} />
                    <Tooltip formatter={(v: number) => [`¥${v.toFixed(2)}`, '月变动']} />
                    <Bar dataKey="change" radius={[4, 4, 0, 0]} maxBarSize={32}
                      shape={(props: any) => {
                        const { x, y, width, height, payload } = props;
                        const fill = payload?.change >= 0 ? '#ff4d4f' : '#52c41a';
                        return <rect x={x} y={y} width={width} height={height} fill={fill} rx={4} ry={4} />;
                      }} />
                  </BarChart>
                </ResponsiveContainer>
              </Card>
            </>
          ),
        },
        {
          key: 'stats',
          label: '📊 统计',
          children: !analysis ? <Card><Text type="secondary">暂无数据</Text></Card> : (
            <Row gutter={[12, 12]}>
              <Col xs={12} sm={6}><Card><Statistic title="胜率" value={analysis.win_rate} suffix="%" valueStyle={{ color: analysis.win_rate >= 50 ? '#ff4d4f' : '#52c41a' }} /></Card></Col>
              <Col xs={12} sm={6}><Card><Statistic title="上涨天" value={dist?.up_days || 0} valueStyle={{ color: '#ff4d4f' }} /></Card></Col>
              <Col xs={12} sm={6}><Card><Statistic title="下跌天" value={dist?.down_days || 0} valueStyle={{ color: '#52c41a' }} /></Card></Col>
              <Col xs={12} sm={6}><Card><Statistic title="持平天" value={dist?.flat_days || 0} /></Card></Col>
              <Col xs={12} sm={6}><Card><Statistic title="最佳单日" value={`+${dist?.best_day?.toFixed(2) || '0.00'}`} valueStyle={{ color: '#ff4d4f' }} /></Card></Col>
              <Col xs={12} sm={6}><Card><Statistic title="最差单日" value={`-${dist?.worst_day?.toFixed(2) || '0.00'}`} valueStyle={{ color: '#52c41a' }} /></Card></Col>
              <Col xs={12} sm={6}><Card><Statistic title="日均盈利" value={`+${dist?.avg_gain?.toFixed(2) || '0.00'}`} valueStyle={{ color: '#ff4d4f' }} /></Card></Col>
              <Col xs={12} sm={6}><Card><Statistic title="日均亏损" value={`-${dist?.avg_loss?.toFixed(2) || '0.00'}`} valueStyle={{ color: '#52c41a' }} /></Card></Col>
              <Col span={24}>
                <Row gutter={12}>
                  <Col xs={24} md={12}>
                    <Card title="📅 近12周" size="small">
                      <Table dataSource={analysis.weekly?.slice(-12) || []} rowKey="week" pagination={false} size="small"
                        columns={[
                          { title: '周', dataIndex: 'week', width: 80 },
                          { title: '变动', dataIndex: 'change', render: (v: number) => <Text strong style={{ color: v >= 0 ? '#ff4d4f' : '#52c41a' }}>{v >= 0 ? '+' : ''}{v?.toFixed(2)}</Text> },
                          { title: '盈亏', dataIndex: 'profit', render: (v: number) => <Text style={{ color: v >= 0 ? '#ff4d4f' : '#52c41a' }}>¥{v?.toFixed(2)}</Text> },
                        ]} />
                    </Card>
                  </Col>
                  <Col xs={24} md={12}>
                    <Card title="📅 近12月" size="small">
                      <Table dataSource={analysis.monthly?.slice(-12) || []} rowKey="month" pagination={false} size="small"
                        columns={[
                          { title: '月', dataIndex: 'month', width: 80 },
                          { title: '变动', dataIndex: 'change', render: (v: number) => <Text strong style={{ color: v >= 0 ? '#ff4d4f' : '#52c41a' }}>{v >= 0 ? '+' : ''}{v?.toFixed(2)}</Text> },
                        ]} />
                    </Card>
                  </Col>
                </Row>
              </Col>
            </Row>
          ),
        },
      ]} />
    </div>
  );
};

export default Dashboard;
