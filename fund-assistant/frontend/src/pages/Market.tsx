import React, { useState, useEffect } from 'react';
import { Typography, Card, Row, Col, Table, Statistic, Tabs, Spin, Tag, Space, Progress, List } from 'antd';
import { RiseOutlined, FallOutlined } from '@ant-design/icons';
import { fundApi } from '@/api/fund';
import client from '@/api/client';

const { Title, Text } = Typography;

const fmtYi = (v?: number) => {
  if (v === undefined || v === null) return '--';
  return `${v >= 0 ? '+' : ''}${v.toFixed(2)}亿`;
};

const Market: React.FC = () => {
  const [indices, setIndices] = useState<any[]>([]);
  const [northFlow, setNorthFlow] = useState<any>({});
  const [mainFlow, setMainFlow] = useState<any>({});
  const [sectorFlow, setSectorFlow] = useState<any[]>([]);
  const [breadth, setBreadth] = useState<any>({});
  const [fundRanks, setFundRanks] = useState<any[]>([]);
  const [news, setNews] = useState<any[]>([]);
  const [rankPeriod, setRankPeriod] = useState('1m');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([
      fundApi.getMarketIndices().then(r => setIndices(r.data || [])),
      fundApi.getNorthFlow().then(r => setNorthFlow(r.data || {})),
      fundApi.getMainFlow().then(r => setMainFlow(r.data || {})),
      fundApi.getSectorFlow(12).then(r => setSectorFlow(r.data || [])),
      client.get('/market/breadth').then(r => setBreadth(r.data || {})),
      client.get('/market/news?limit=10').then(r => setNews(r.data || [])),
    ]).finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    fundApi.getMarketIndices().then(r => {
      setFundRanks(r.data || []);
    });
  }, [rankPeriod]);

  const loadFundRanks = async (p: string) => {
    setRankPeriod(p);
    try {
      const res = await client.get(`/market/fund-ranks?period=${p}&limit=20`);
      setFundRanks(res.data || []);
    } catch {}
  };

  useEffect(() => { loadFundRanks(rankPeriod); }, []);

  const totalStocks = (breadth.up || 0) + (breadth.down || 0);
  const upPct = totalStocks > 0 ? ((breadth.up || 0) / totalStocks * 100) : 0;

  return (
    <div>
      <Title level={3} style={{ marginBottom: 12 }}>📈 市场行情</Title>

      {/* 大盘指数 */}
      <Row gutter={[8, 8]} style={{ marginBottom: 16 }}>
        {indices.slice(0, 7).map((idx: any) => (
          <Col xs={12} sm={8} md={6} lg={3} key={idx.code}>
            <Card hoverable size="small" bodyStyle={{ padding: '10px 12px' }}>
              <Text type="secondary" style={{ fontSize: 11 }}>{idx.name}</Text>
              <br />
              <Text strong style={{ fontSize: 16 }}>{idx.current_point?.toFixed(2) || '--'}</Text>
              <br />
              <Text style={{ fontSize: 13, color: (idx.change_pct || 0) >= 0 ? '#ff4d4f' : '#52c41a' }}>
                {(idx.change_pct || 0) >= 0 ? '+' : ''}{idx.change_pct?.toFixed(2)}%
              </Text>
            </Card>
          </Col>
        ))}
      </Row>

      <Tabs defaultActiveKey="flow" items={[
        {
          key: 'flow',
          label: '💸 资金流向',
          children: (
            <Spin spinning={loading}>
              <Row gutter={[12, 12]} style={{ marginBottom: 12 }}>
                <Col xs={24} md={12}>
                  <Card title="🇭🇰 北向资金" size="small">
                    {northFlow?.net_flow_yi !== undefined ? (
                      <Statistic value={fmtYi(northFlow.net_flow_yi)} valueStyle={{ color: (northFlow.net_flow_yi || 0) >= 0 ? '#ff4d4f' : '#52c41a', fontSize: 24 }} />
                    ) : <Text type="secondary">非交易时段</Text>}
                  </Card>
                </Col>
                <Col xs={24} md={12}>
                  <Card title="💰 主力资金" size="small">
                    {mainFlow?.main_net_flow_yi !== undefined ? (
                      <Statistic value={fmtYi(mainFlow.main_net_flow_yi)} valueStyle={{ color: (mainFlow.main_net_flow_yi || 0) >= 0 ? '#ff4d4f' : '#52c41a', fontSize: 24 }} />
                    ) : <Text type="secondary">非交易时段</Text>}
                  </Card>
                </Col>
              </Row>

              {/* 市场宽度 */}
              {totalStocks > 0 && (
                <Card title="📊 市场宽度" size="small" style={{ marginBottom: 12 }}>
                  <Row gutter={16}>
                    <Col span={12}>
                      <Statistic title="上涨家数" value={breadth.up} valueStyle={{ color: '#ff4d4f' }} suffix={<span style={{ fontSize: 13 }}>{upPct.toFixed(1)}%</span>} />
                    </Col>
                    <Col span={12}>
                      <Statistic title="下跌家数" value={breadth.down} valueStyle={{ color: '#52c41a' }} suffix={<span style={{ fontSize: 13 }}>{(100 - upPct).toFixed(1)}%</span>} />
                    </Col>
                  </Row>
                  <Progress percent={upPct} strokeColor="#ff4d4f" trailColor="#52c41a" showInfo={false} style={{ marginTop: 8 }} />
                </Card>
              )}

              <Card title="🏢 板块资金流向" size="small">
                <Table dataSource={sectorFlow} rowKey="code" pagination={false} size="small"
                  columns={[
                    { title: '板块', dataIndex: 'name', width: 100 },
                    { title: '涨跌', dataIndex: 'change_pct', width: 70, render: (v: number) => <Text style={{ color: v >= 0 ? '#ff4d4f' : '#52c41a' }}>{v >= 0 ? '+' : ''}{v?.toFixed(2)}%</Text> },
                    { title: '主力净流入', dataIndex: 'net_flow_yi', width: 100, render: (v: number) => <Text style={{ color: v >= 0 ? '#ff4d4f' : '#52c41a' }}>{fmtYi(v)}</Text> },
                    { title: '5日流入', dataIndex: 'net_flow_5d_yi', render: (v: number) => fmtYi(v) },
                  ]}
                  locale={{ emptyText: '非交易时段' }} />
              </Card>
            </Spin>
          ),
        },
        {
          key: 'ranks',
          label: '📊 基金排行',
          children: (
            <Card>
              <Space style={{ marginBottom: 12 }}>
                {['1m', '3m', '6m', '1y'].map(p => (
                  <Tag.CheckableTag key={p} checked={rankPeriod === p} onChange={() => loadFundRanks(p)}>
                    {{ '1m': '近1月', '3m': '近3月', '6m': '近6月', '1y': '近1年' }[p]}
                  </Tag.CheckableTag>
                ))}
              </Space>
              <Table dataSource={fundRanks} rowKey="code" pagination={{ pageSize: 15 }} size="small"
                columns={[
                  { title: '基金', dataIndex: 'name', width: 180, render: (n: string, r: any) => <div><Text strong>{n}</Text><br /><Text type="secondary" style={{ fontSize: 11 }}>{r.code} | {r.type}</Text></div> },
                  { title: '近1月', dataIndex: 'return_1m', render: (v: number) => <Text style={{ color: v >= 0 ? '#ff4d4f' : '#52c41a' }}>{v >= 0 ? '+' : ''}{v?.toFixed(2)}%</Text> },
                  { title: '近3月', dataIndex: 'return_3m', render: (v: number) => <Text style={{ color: v >= 0 ? '#ff4d4f' : '#52c41a' }}>{v >= 0 ? '+' : ''}{v?.toFixed(2)}%</Text> },
                  { title: '近6月', dataIndex: 'return_6m', render: (v: number) => <Text style={{ color: v >= 0 ? '#ff4d4f' : '#52c41a' }}>{v >= 0 ? '+' : ''}{v?.toFixed(2)}%</Text> },
                  { title: '近1年', dataIndex: 'return_1y', render: (v: number) => <Text style={{ color: v >= 0 ? '#ff4d4f' : '#52c41a' }}>{v >= 0 ? '+' : ''}{v?.toFixed(2)}%</Text> },
                ]}
                locale={{ emptyText: '加载中...' }} />
            </Card>
          ),
        },
        {
          key: 'news',
          label: '📰 快讯',
          children: (
            <Card>
              <List dataSource={news} loading={loading}
                renderItem={(item: any) => (
                  <List.Item style={{ padding: '6px 0' }}>
                    <Text style={{ fontSize: 13 }}>{item.title}</Text>
                    <Text type="secondary" style={{ fontSize: 11, marginLeft: 8 }}>{item.time}</Text>
                  </List.Item>
                )}
                locale={{ emptyText: '暂无快讯' }} />
            </Card>
          ),
        },
      ]} />
    </div>
  );
};

export default Market;