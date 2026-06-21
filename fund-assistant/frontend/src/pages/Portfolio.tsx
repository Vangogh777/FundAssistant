import React, { useState, useEffect } from 'react';
import {
  Typography, Table, Button, Modal, Form, Input, InputNumber, DatePicker,
  AutoComplete, Space, Popconfirm, message, Card, Tag, Segmented,
  Divider, Timeline, Drawer, Tooltip
} from 'antd';
import {
  PlusOutlined, SearchOutlined, EditOutlined, DeleteOutlined, ReloadOutlined,
  CameraOutlined, HistoryOutlined, InfoCircleOutlined
} from '@ant-design/icons';
import { fundApi } from '@/api/fund';
import SyncModal from '@/components/SyncModal';
import dayjs from 'dayjs';

const { Title, Text } = Typography;

interface FundSuggestion { code: string; name: string; type: string; nav: number; estimate_change_pct: number; }
interface PortfolioItem {
  id: number; fund_code: string; fund_name: string; fund_type: string;
  shares: number; cost_per_share: number; total_cost: number; buy_date: string;
  fee: number; note: string; estimated_nav: number; current_nav: number;
  market_value: number; profit_loss: number; profit_loss_pct: number;
}

type EntryMode = 'new' | 'existing';

const Portfolio: React.FC = () => {
  const [portfolios, setPortfolios] = useState<PortfolioItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [modalOpen, setModalOpen] = useState(false);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [entryMode, setEntryMode] = useState<EntryMode>('new');
  const [form] = Form.useForm();

  const [searchKw, setSearchKw] = useState('');
  const [suggestions, setSuggestions] = useState<FundSuggestion[]>([]);
  const [selectedFundNav, setSelectedFundNav] = useState<number>(0);
  const [autoRefresh, setAutoRefresh] = useState(true);
  const [syncOpen, setSyncOpen] = useState(false);

  // 修改历史
  const [historyDrawerOpen, setHistoryDrawerOpen] = useState(false);
  const [historyData, setHistoryData] = useState<any[]>([]);
  const [historyLoading, setHistoryLoading] = useState(false);
  const [historyPortfolio, setHistoryPortfolio] = useState<PortfolioItem | null>(null);

  useEffect(() => { loadPortfolios(); }, []);
  // 定时刷新（每60秒）
  useEffect(() => {
    if (!autoRefresh) return;
    const timer = setInterval(loadPortfolios, 60000);
    return () => clearInterval(timer);
  }, [autoRefresh]);

  const loadPortfolios = async () => {
    setLoading(true);
    try { const res = await fundApi.getPortfolios(); setPortfolios(res.data); }
    catch { message.error('加载持仓失败'); }
    finally { setLoading(false); }
  };

  const handleSearch = async (kw: string) => {
    setSearchKw(kw);
    if (kw.length < 2) { setSuggestions([]); return; }
    try { const res = await fundApi.search(kw); setSuggestions(res.data || []); }
    catch { setSuggestions([]); }
  };

  const checkExistingHolding = (code: string, name: string) => {
    const existing = portfolios.find(p => p.fund_code === code);
    if (existing && !editingId) {
      Modal.confirm({
        title: '该基金已在持仓中',
        content: `「${name || code}」已持有 ${existing.shares} 份，市值 ¥${existing.market_value.toFixed(0)}，是否修改原持仓？`,
        okText: '修改原持仓',
        cancelText: '新增一条',
        onOk: () => handleEdit(existing),
      });
    }
  };

  const handleSelectFund = (code: string) => {
    const fund = suggestions.find(f => f.code === code);
    if (!fund) return;
    setSelectedFundNav(fund.nav || 0);
    form.setFieldsValue({ fund_code: fund.code, fund_name: fund.name });
    checkExistingHolding(fund.code, fund.name);
  };

  const handleSubmit = async () => {
    try {
      const values = await form.validateFields();
      let payload: any = { fund_code: values.fund_code, note: values.note || '' };

      if (entryMode === 'new') {
        // 新买入：只需投资金额
        payload.investment_amount = parseFloat(values.investment_amount || '0');
        if (!payload.investment_amount || payload.investment_amount <= 0) {
          message.error('请输入买入金额'); return;
        }
        if (values.buy_date) payload.buy_date = values.buy_date.format('YYYY-MM-DD');
        const now = dayjs().format('YYYY-MM-DDTHH:mm:ss');
        payload.buy_time = now;
        payload.fee = values.fee || 0;
      } else {
        // 原本持有：传市值+盈亏给后端，用实时净值计算
        const currentValue = parseFloat(values.current_value || '0');
        const currentProfit = parseFloat(values.current_profit || '0');
        if (!currentValue || currentValue <= 0) { message.error('请输入当前市值'); return; }
        payload.current_value = currentValue;
        payload.current_profit = currentProfit || 0;
        payload.buy_date = values.buy_date ? values.buy_date.format('YYYY-MM-DD') : dayjs().format('YYYY-MM-DD');
      }

      if (editingId) {
        await fundApi.updatePortfolio(editingId, payload);
        message.success('更新成功');
      } else {
        await fundApi.addPortfolio(payload);
        message.success('添加成功');
      }
      setModalOpen(false); form.resetFields(); setEditingId(null); setEntryMode('new');
      loadPortfolios();
    } catch { /* validate error */ }
  };

  const handleEdit = (record: PortfolioItem) => {
    setEditingId(record.id);
    // 编辑时默认进入"原本持有"模式，预填当前市值和盈亏
    setEntryMode('existing');
    form.setFieldsValue({
      fund_code: record.fund_code, fund_name: record.fund_name,
      current_value: record.market_value,
      current_profit: record.profit_loss,
      buy_date: dayjs(record.buy_date),
    });
    setModalOpen(true);
  };

  const handleDelete = async (id: number) => {
    await fundApi.deletePortfolio(id);
    message.success('删除成功');
    loadPortfolios();
  };

  const showHistory = async (record: PortfolioItem) => {
    setHistoryDrawerOpen(true);
    setHistoryPortfolio(record);
    setHistoryLoading(true);
    try { const res = await fundApi.getPortfolioHistory(record.id); setHistoryData(res.data); }
    catch { setHistoryData([]); }
    finally { setHistoryLoading(false); }
  };

  const openModal = () => {
    setEditingId(null); setEntryMode('new'); form.resetFields();
    setSearchKw(''); setSuggestions([]); setModalOpen(true);
  };

  // 今日盈亏 = 份额 * 估算净值变化 (昨日收盘 → 今日估算)
  const todayPL = (r: PortfolioItem) => {
    if (!r.estimated_nav || !r.current_nav || r.current_nav === r.estimated_nav) return null;
    return r.shares * (r.estimated_nav - r.current_nav);
  };

  const columns = [
    {
      title: '基金名称', dataIndex: 'fund_name', key: 'name', width: 140,
      render: (name: string, r: PortfolioItem) => (
        <div><Text strong>{name || '--'}</Text><br /><Text type="secondary" style={{ fontSize: 12 }}>{r.fund_code}</Text></div>
      ),
    },
    { title: '份额', dataIndex: 'shares', key: 'shares', width: 75, responsive: ['sm' as const], render: (v: number) => v.toLocaleString() },
    { title: '成本', dataIndex: 'total_cost', key: 'cost', width: 80, responsive: ['sm' as const], render: (v: number) => `¥${v.toFixed(0)}` },
    { title: '市值', dataIndex: 'market_value', key: 'market', width: 85, render: (v: number) => `¥${v.toFixed(0)}` },
    {
      title: '今日盈亏', key: 'today', width: 100,
      render: (_: unknown, r: PortfolioItem) => {
        const pl = todayPL(r);
        if (pl === null) return <Text type="secondary">--</Text>;
        return <Text strong style={{ color: pl >= 0 ? '#ff4d4f' : '#52c41a', fontSize: 14 }}>
          {pl >= 0 ? '+' : ''}¥{pl.toFixed(2)}
        </Text>;
      },
    },
    {
      title: '累计盈亏', key: 'pl', width: 120,
      sorter: (a: PortfolioItem, b: PortfolioItem) => a.profit_loss - b.profit_loss,
      render: (_: unknown, r: PortfolioItem) => (
        <div>
          <Text strong style={{ color: r.profit_loss >= 0 ? '#ff4d4f' : '#52c41a', fontSize: 14 }}>
            {r.profit_loss >= 0 ? '+' : ''}¥{r.profit_loss.toFixed(2)}
          </Text>
          <br /><Text style={{ color: r.profit_loss_pct >= 0 ? '#ff4d4f' : '#52c41a', fontSize: 11 }}>
            {r.profit_loss_pct >= 0 ? '+' : ''}{r.profit_loss_pct.toFixed(2)}%
          </Text>
        </div>
      ),
    },
    {
      title: '操作', key: 'actions', width: 110,
      render: (_: unknown, r: PortfolioItem) => (
        <Space size="small">
          <Tooltip title="修改历史"><Button type="link" size="small" icon={<HistoryOutlined />} onClick={() => showHistory(r)} /></Tooltip>
          <Button type="link" size="small" icon={<EditOutlined />} onClick={() => handleEdit(r)} />
          <Popconfirm title="确认删除？" onConfirm={() => handleDelete(r.id)}>
            <Button type="link" danger size="small" icon={<DeleteOutlined />} />
          </Popconfirm>
        </Space>
      ),
    },
  ];

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16, flexWrap: 'wrap', gap: 8 }}>
        <Title level={3} style={{ margin: 0 }}>📋 持仓管理</Title>
        <Space wrap>
          <Button icon={<ReloadOutlined />} onClick={loadPortfolios}>刷新</Button>
          <Button type={autoRefresh ? 'primary' : 'default'} size="small"
            onClick={() => setAutoRefresh(!autoRefresh)}
            style={{ fontSize: 12 }}>
            {autoRefresh ? '⏱ 自动刷新中' : '▶ 开启自动刷新'}
          </Button>
          <Button type="primary" icon={<PlusOutlined />} onClick={openModal}>添加持仓</Button>
          <Button icon={<CameraOutlined />} onClick={() => setSyncOpen(true)}>同步持仓</Button>
        </Space>
        <SyncModal open={syncOpen} onClose={() => setSyncOpen(false)} onImported={loadPortfolios} />
      </div>

      <Card>
        <Table dataSource={portfolios} columns={columns} rowKey="id" loading={loading}
          pagination={{ pageSize: 20 }} scroll={{ x: 600 }} size="middle"
          locale={{ emptyText: '暂无持仓，点击「添加持仓」开始记录' }} />
      </Card>

      {/* 添加/编辑弹窗 */}
      <Modal title={editingId ? '编辑持仓' : '添加持仓'} open={modalOpen} onOk={handleSubmit}
        onCancel={() => { setModalOpen(false); form.resetFields(); setEditingId(null); }} width={560} destroyOnClose>
        <Form form={form} layout="vertical" style={{ marginTop: 8 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16, flexWrap: 'wrap', gap: 8 }}>
            <Segmented value={entryMode} onChange={(v) => setEntryMode(v as EntryMode)}
              options={[{ value: 'new', label: '🆕 新买入' }, { value: 'existing', label: '📋 原本持有' }]} />

          </div>

          <Form.Item label="搜索基金">
            <AutoComplete style={{ width: '100%' }} placeholder="输入基金名称或代码搜索"
              onSearch={handleSearch} value={searchKw}
              options={suggestions.map(f => ({ value: f.code, label: <div style={{ display: 'flex', justifyContent: 'space-between' }}><span>{f.name}</span><Text type="secondary">{f.code}</Text></div> }))}
              onSelect={handleSelectFund}>
              <Input prefix={<SearchOutlined />} />
            </AutoComplete>
          </Form.Item>

          <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap' }}>
            <Form.Item label="基金代码" name="fund_code" rules={[{ required: true, message: '请选择基金' }]} style={{ flex: 1, minWidth: 120 }}>
              <Input disabled placeholder="搜索后自动填充" />
            </Form.Item>
            <Form.Item label="基金名称" name="fund_name" style={{ flex: 2, minWidth: 180 }}>
              <Input disabled placeholder="自动填充" />
            </Form.Item>
          </div>

          <Divider style={{ margin: '8px 0 16px' }} />

          {entryMode === 'new' && (
            <>
              <Form.Item
                label={editingId ? '投入金额（元）' : (
                  <span>买入金额 <Tooltip title="只需填写买入花了多少钱，系统自动根据时间计算份额和净值"><InfoCircleOutlined style={{ color: '#1677ff' }} /></Tooltip></span>
                )}
                name="investment_amount"
                rules={[{ required: true, message: '请输入买入金额' }]}
              >
                <InputNumber style={{ width: '100%' }} min={0.01} step={100} precision={2} prefix="¥" placeholder="例如 10000.00" size="large" />
              </Form.Item>
              {selectedFundNav > 0 && (
                <div style={{ background: 'var(--bg-elevated, #f0f5ff)', padding: 12, borderRadius: 8, marginBottom: 12 }}>
                  <Text type="secondary">📊 系统将自动根据买入时间判断净值日期（下午3点前用当天，3点后用下一交易日）</Text>
                  <br />
                  <Text>  参考最新净值：<Text strong>¥{selectedFundNav.toFixed(4)}</Text>（实际以交易时间为准）</Text>
                </div>
              )}
              <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap' }}>
                <Form.Item label="买入日期" name="buy_date" style={{ flex: 1, minWidth: 140 }}>
                  <DatePicker style={{ width: '100%' }} placeholder="不填用今天" />
                </Form.Item>
                <Form.Item label="手续费" name="fee" style={{ flex: 1, minWidth: 100 }}>
                  <InputNumber style={{ width: '100%' }} min={0} step={0.01} precision={2} placeholder="0.00" />
                </Form.Item>
              </div>
            </>
          )}

          {entryMode === 'existing' && (
            <>
              <div style={{ background: 'linear-gradient(135deg, #1e3a5f22, #1677ff11)', padding: 16, borderRadius: 10, marginBottom: 16 }}>
                <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap' }}>
                  <Form.Item label="当前市值（元）" name="current_value" rules={[{ required: true, message: '如 8528' }]} style={{ flex: 1, minWidth: 140 }}>
                    <InputNumber style={{ width: '100%' }} min={0.01} step={100} precision={2} prefix="¥" placeholder="你在 App 看到的市值" size="large" />
                  </Form.Item>
                  <Form.Item label="当前盈亏（元）" name="current_profit" style={{ flex: 1, minWidth: 140 }}>
                    <InputNumber style={{ width: '100%' }} step={0.01} precision={2} placeholder="盈利+720，亏损-300" size="large" />
                  </Form.Item>
                </div>
                <Form.Item label="买入日期（必填，用于收益分析）" name="buy_date" rules={[{ required: true, message: '请选择买入日期，用于计算实际收益' }]} style={{ marginBottom: 8 }}>
                  <DatePicker style={{ width: '100%' }} placeholder="选择买入日期" />
                </Form.Item>
                <Text type="secondary">
                  💡 市值 - 盈亏 = 总成本，系统用实时净值自动算份额
                </Text>
              </div>
            </>
          )}

          <Form.Item label="备注" name="note">
            <Input.TextArea rows={2} placeholder="可选备注" />
          </Form.Item>
        </Form>
      </Modal>

      {/* 修改历史抽屉 */}
      <Drawer title={historyPortfolio ? `📝 ${historyPortfolio.fund_name} 修改记录` : '修改记录'}
        open={historyDrawerOpen} onClose={() => setHistoryDrawerOpen(false)} width={420}>
        {historyLoading ? <Text type="secondary">加载中...</Text> : historyData.length === 0 ? <Text type="secondary">暂无修改记录</Text> : (
          <Timeline items={historyData.map((h: any) => ({
            color: h.change_type === 'create' ? 'green' : h.change_type === 'delete' ? 'red' : 'blue',
            children: (
              <div>
                <Tag color={h.change_type === 'create' ? 'green' : h.change_type === 'delete' ? 'red' : 'blue'}>
                  {h.change_type === 'create' ? '创建' : h.change_type === 'delete' ? '删除' : '修改'}
                </Tag>
                <Text type="secondary" style={{ fontSize: 12, display: 'block' }}>{dayjs(h.created_at).format('YYYY-MM-DD HH:mm')}</Text>
                {h.change_fields?.length > 0 && <Text style={{ fontSize: 12 }}>变更: {h.change_fields.join(', ')}</Text>}
                {h.note && <Text style={{ fontSize: 12, display: 'block' }}>{h.note}</Text>}
                {h.after_snapshot?.shares && (
                  <Text type="secondary" style={{ fontSize: 12, display: 'block' }}>
                    → {h.after_snapshot.shares}份 ¥{h.after_snapshot.cost_per_share}/份
                  </Text>
                )}
              </div>
            ),
          }))} />
        )}
      </Drawer>
    </div>
  );
};

export default Portfolio;
