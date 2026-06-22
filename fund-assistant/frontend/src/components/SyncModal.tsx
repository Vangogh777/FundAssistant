import React, { useState, useRef } from 'react';
import { Modal, Tabs, Button, Upload, Input, Table, Checkbox, message, Space, Tag, Spin, InputNumber, Alert, Divider } from 'antd';
import { UploadOutlined, CameraOutlined, InboxOutlined, NumberOutlined, FileTextOutlined } from '@ant-design/icons';
import { fundApi } from '@/api/fund';
import client from '@/api/client';

const { TextArea } = Input;

interface Props {
  open: boolean;
  onClose: () => void;
  onImported: () => void;
}

interface RecognizedFund {
  fund_name: string;
  fund_code: string;
  current_value: number;
  current_profit: number;
  shares?: number;
  cost_per_share?: number;
  total_cost?: number;
  buy_date?: string;
  note?: string;
  valid?: boolean;
  nav?: number;
  estimated_nav?: number;
  estimate_change_pct?: number;
  fund_type?: string;
  row?: number;
}

interface CsvError {
  row: number;
  fund_code?: string;
  error: string;
}

const SyncModal: React.FC<Props> = ({ open, onClose, onImported }) => {
  const [loading, setLoading] = useState(false);
  const [funds, setFunds] = useState<RecognizedFund[]>([]);
  const [selected, setSelected] = useState<Set<number>>(new Set());
  const [importing, setImporting] = useState(false);
  const [textInput, setTextInput] = useState('');
  const [codesInput, setCodesInput] = useState('');
  const [csvErrors, setCsvErrors] = useState<CsvError[]>([]);
  const [importMode, setImportMode] = useState<'ocr' | 'csv'>('ocr');
  const fileRef = useRef<HTMLInputElement>(null);
  const csvRef = useRef<HTMLInputElement>(null);

  const handleOCRResult = (data: any) => {
    const list = data?.all_funds || (data?.fund_name ? [data] : []);
    if (list.length === 0) {
      message.warning('未识别到基金信息');
      return;
    }
    setFunds(list);
    setSelected(new Set(list.map((_: any, i: number) => i)));
    setCsvErrors([]);
    setImportMode('ocr');
  };

  const handleUpload = async (file: File) => {
    setLoading(true);
    try {
      const formData = new FormData();
      formData.append('file', file);
      const res = await fetch('/api/ocr/parse', {
        method: 'POST', body: formData,
        headers: { Authorization: `Bearer ${localStorage.getItem('access_token')}` },
      });
      handleOCRResult(await res.json());
    } catch { message.error('识别失败'); }
    finally { setLoading(false); }
  };

  const handlePaste = async () => {
    if (!textInput.trim()) return;
    setLoading(true);
    try {
      const res = await fetch('/api/ocr/parse-text', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${localStorage.getItem('access_token')}` },
        body: JSON.stringify({ text: textInput }),
      });
      handleOCRResult(await res.json());
    } catch { message.error('识别失败'); }
    finally { setLoading(false); }
  };

  // 批量解析基金代码
  const handleParseCodes = async () => {
    if (!codesInput.trim()) return;
    setLoading(true);
    try {
      const res = await fetch('/api/portfolio/parse-codes', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${localStorage.getItem('access_token')}` },
        body: JSON.stringify({ codes: codesInput }),
      });
      const data = await res.json();
      if (data.error) {
        message.warning(data.error);
        return;
      }
      const list = data.funds || [];
      if (list.length === 0) {
        message.warning('未识别到有效基金代码');
        return;
      }
      setFunds(list.map((f: any) => ({
        ...f,
        current_value: 0,
        current_profit: 0,
        shares: 0,
        cost_per_share: 0,
      })));
      setSelected(new Set(list.map((_: any, i: number) => i)));
      setCsvErrors([]);
      setImportMode('ocr');
      message.success(`识别到 ${list.length} 只基金，其中 ${data.valid} 只有效`);
    } catch { message.error('查询失败'); }
    finally { setLoading(false); }
  };

  // CSV 文件上传
  const handleCSVUpload = async (file: File) => {
    setLoading(true);
    setCsvErrors([]);
    try {
      const formData = new FormData();
      formData.append('file', file);
      const res = await fetch('/api/portfolio/import-csv', {
        method: 'POST', body: formData,
        headers: { Authorization: `Bearer ${localStorage.getItem('access_token')}` },
      });
      const data = await res.json();

      if (data.errors && data.errors.length > 0) {
        setCsvErrors(data.errors);
      }

      if (data.data && data.data.length > 0) {
        setFunds(data.data);
        setSelected(new Set(data.data.map((_: any, i: number) => i)));
        setImportMode('csv');
        message.success(`解析成功：${data.valid}/${data.total} 条有效`);
      } else if (data.errors && data.errors.length > 0) {
        message.warning(`解析完成，但有 ${data.errors.length} 条错误`);
      } else {
        message.warning('CSV 文件为空或无有效数据');
      }
    } catch (err) {
      message.error('CSV 解析失败');
    }
    finally { setLoading(false); }
  };

  const handleImport = async () => {
    setImporting(true);
    try {
      const toImport = funds.filter((_, i) => selected.has(i));
      const payload = toImport.map((f: any) => ({
        fund_code: f.fund_code || '',
        fund_name: f.fund_name || '',
        current_value: f.current_value || 0,
        current_profit: f.current_profit || 0,
        shares: f.shares || 0,
        cost_per_share: f.cost_per_share || 0,
        buy_date: f.buy_date || '',
        note: f.note || '',
      }));
      await fundApi.batchAddPortfolios(payload);
      message.success(`成功导入 ${toImport.length} 只基金`);
      onImported();
      onClose();
      setFunds([]);
      setTextInput('');
      setCodesInput('');
      setCsvErrors([]);
    } catch { message.error('导入失败'); }
    finally { setImporting(false); }
  };

  // 根据导入模式显示不同的列
  const isCsvMode = importMode === 'csv' && funds.length > 0 && funds[0].shares && funds[0].cost_per_share;

  return (
    <Modal title="📥 同步持仓" open={open} onCancel={onClose} width={750}
      footer={funds.length > 0 ? [
        <Button key="cancel" onClick={onClose}>取消</Button>,
        <Button key="import" type="primary" loading={importing} onClick={handleImport}
          disabled={selected.size === 0}>
          导入选中 ({selected.size})
        </Button>,
      ] : null}
    >
      <Tabs items={[
        {
          key: 'upload',
          label: <span><CameraOutlined /> 上传截图</span>,
          children: (
            <div style={{ textAlign: 'center', padding: 24 }}>
              <input ref={fileRef} type="file" accept="image/*" style={{ display: 'none' }}
                onChange={(e) => { const f = e.target.files?.[0]; if (f) handleUpload(f); e.target.value = ''; }} />
              <Button size="large" icon={<UploadOutlined />} loading={loading}
                onClick={() => fileRef.current?.click()}>
                选择支付宝/微信截图
              </Button>
              <div style={{ marginTop: 12 }}>
                <span style={{ color: '#888', fontSize: 12 }}>支持支付宝、天天基金等 App 持仓截图</span>
              </div>
            </div>
          ),
        },
        {
          key: 'text',
          label: '📋 粘贴文字',
          children: (
            <div>
              <TextArea rows={8} value={textInput} onChange={e => setTextInput(e.target.value)}
                placeholder="在微信里长按支付宝截图 → 提取文字 → 复制 → 粘贴到这里" />
              <Button type="primary" onClick={handlePaste} loading={loading} style={{ marginTop: 12 }}
                disabled={!textInput.trim()}>
                识别
              </Button>
            </div>
          ),
        },
        {
          key: 'csv',
          label: <span><FileTextOutlined /> 导入CSV</span>,
          children: (
            <div>
              <input ref={csvRef} type="file" accept=".csv,.txt" style={{ display: 'none' }}
                onChange={(e) => { const f = e.target.files?.[0]; if (f) handleCSVUpload(f); e.target.value = ''; }} />
              <div style={{ textAlign: 'center', marginBottom: 16 }}>
                <Button size="large" icon={<UploadOutlined />} loading={loading}
                  onClick={() => csvRef.current?.click()}>
                  选择 CSV 文件
                </Button>
              </div>
              <Divider style={{ margin: '12px 0' }} />
              <div style={{ color: '#666', fontSize: 13 }}>
                <div style={{ marginBottom: 8 }}><strong>支持两种格式：</strong></div>
                <div style={{ marginBottom: 12 }}>
                  <Tag color="blue">简单格式</Tag> 基金代码,份额,成本价（无表头）
                  <pre style={{ background: '#f5f5f5', padding: 8, borderRadius: 4, marginTop: 4, fontSize: 12 }}>
{`110011,1000,2.35
161725,500,1.28
519778,2000,1.56`}
                  </pre>
                </div>
                <div>
                  <Tag color="green">完整格式</Tag> 带表头
                  <pre style={{ background: '#f5f5f5', padding: 8, borderRadius: 4, marginTop: 4, fontSize: 12 }}>
{`基金代码,基金名称,份额,成本价,买入日期,备注
110011,易方达中小盘,1000,2.35,2024-01-15,定投
161725,招商中证白酒,500,1.28,,手动`}
                  </pre>
                </div>
              </div>
            </div>
          ),
        },
        {
          key: 'codes',
          label: <span><NumberOutlined /> 批量代码</span>,
          children: (
            <div>
              <TextArea rows={6} value={codesInput} onChange={e => setCodesInput(e.target.value)}
                placeholder="粘贴基金代码，支持多种格式：&#10;110011&#10;161725, 519778&#10;004854 007301 159915" />
              <Button type="primary" onClick={handleParseCodes} loading={loading} style={{ marginTop: 12 }}
                disabled={!codesInput.trim()}>
                查询基金信息
              </Button>
            </div>
          ),
        },
      ]} />

      {/* CSV 错误提示 */}
      {csvErrors.length > 0 && (
        <Alert
          type="warning"
          style={{ marginTop: 12 }}
          message={`解析警告：${csvErrors.length} 条数据有误`}
          description={
            <div style={{ maxHeight: 100, overflow: 'auto', fontSize: 12 }}>
              {csvErrors.slice(0, 5).map((err, i) => (
                <div key={i}>
                  行 {err.row}: {err.fund_code ? `[${err.fund_code}] ` : ''}{err.error}
                </div>
              ))}
              {csvErrors.length > 5 && <div style={{ color: '#999' }}>... 还有 {csvErrors.length - 5} 条错误</div>}
            </div>
          }
        />
      )}

      {funds.length > 0 && (
        <div style={{ marginTop: 16 }}>
          <Table
            dataSource={funds}
            rowKey={(_, i) => String(i)}
            pagination={false}
            size="small"
            scroll={{ x: 'max-content' }}
            columns={[
              {
                title: '', width: 40, fixed: 'left',
                render: (_: any, __: any, i: number) => (
                  <Checkbox checked={selected.has(i)} onChange={e => {
                    const next = new Set(selected);
                    e.target.checked ? next.add(i) : next.delete(i);
                    setSelected(next);
                  }} />
                ),
              },
              { title: '基金名称', dataIndex: 'fund_name', key: 'name', ellipsis: true },
              { title: '代码', dataIndex: 'fund_code', key: 'code', width: 80, render: (v: string, r: any) =>
                v ? <Tag color={r.valid === false ? 'error' : 'blue'}>{v}</Tag> : <Tag color="default">未匹配</Tag> },
              // CSV 模式显示份额、成本价、总成本
              ...(isCsvMode ? [
                { title: '份额', dataIndex: 'shares', key: 'shares', width: 90, align: 'right' as const, render: (v: number) =>
                  v ? v.toLocaleString() : '-' },
                { title: '成本价', dataIndex: 'cost_per_share', key: 'cost', width: 80, align: 'right' as const, render: (v: number) =>
                  v ? `¥${v.toFixed(4)}` : '-' },
                { title: '总成本', dataIndex: 'total_cost', key: 'tcost', width: 100, align: 'right' as const, render: (v: number) =>
                  v ? `¥${v.toLocaleString()}` : '-' },
                { title: '买入日期', dataIndex: 'buy_date', key: 'bdate', width: 100, render: (v: string) =>
                  v || '-' },
              ] : [
                // OCR 模式显示净值、市值、盈亏
                { title: '净值', dataIndex: 'estimated_nav', key: 'nav', width: 80, align: 'right' as const, render: (v: number) =>
                  v ? v.toFixed(4) : '-' },
                { title: '估算涨跌', dataIndex: 'estimate_change_pct', key: 'chg', width: 80, render: (v: number) =>
                  v ? <span style={{ color: v >= 0 ? '#ff4d4f' : '#52c41a' }}>{v >= 0 ? '+' : ''}{v.toFixed(2)}%</span> : '-' },
                { title: '市值', dataIndex: 'current_value', key: 'val', width: 100, align: 'right' as const, render: (v: number) =>
                  v ? `¥${v?.toLocaleString()}` : '-' },
                { title: '盈亏', dataIndex: 'current_profit', key: 'pl', width: 100, render: (v: number) =>
                  v ? <span style={{ color: v >= 0 ? '#ff4d4f' : '#52c41a' }}>{v >= 0 ? '+' : ''}¥{v?.toLocaleString()}</span> : '-' },
              ]),
            ]}
          />
        </div>
      )}
    </Modal>
  );
};

export default SyncModal;
