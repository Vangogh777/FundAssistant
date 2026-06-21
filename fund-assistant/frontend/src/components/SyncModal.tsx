import React, { useState, useRef } from 'react';
import { Modal, Tabs, Button, Upload, Input, Table, Checkbox, message, Space, Tag, Spin } from 'antd';
import { UploadOutlined, CameraOutlined, InboxOutlined } from '@ant-design/icons';
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
  current_value: number;
  current_profit: number;
}

const SyncModal: React.FC<Props> = ({ open, onClose, onImported }) => {
  const [loading, setLoading] = useState(false);
  const [funds, setFunds] = useState<RecognizedFund[]>([]);
  const [selected, setSelected] = useState<Set<number>>(new Set());
  const [importing, setImporting] = useState(false);
  const [textInput, setTextInput] = useState('');
  const fileRef = useRef<HTMLInputElement>(null);

  const handleOCRResult = (data: any) => {
    const list = data?.all_funds || (data?.fund_name ? [data] : []);
    if (list.length === 0) {
      message.warning('未识别到基金信息');
      return;
    }
    setFunds(list);
    setSelected(new Set(list.map((_: any, i: number) => i)));
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

  const handleImport = async () => {
    setImporting(true);
    try {
      const toImport = funds.filter((_, i) => selected.has(i));
      const payload = toImport.map((f: any) => ({
        fund_code: f.fund_code || '',
        fund_name: f.fund_name || '',
        current_value: f.current_value || 0,
        current_profit: f.current_profit || 0,
      }));
      await fundApi.batchAddPortfolios(payload);
      message.success(`成功导入 ${toImport.length} 只基金`);
      onImported();
      onClose();
      setFunds([]);
      setTextInput('');
    } catch { message.error('导入失败'); }
    finally { setImporting(false); }
  };

  return (
    <Modal title="📥 同步持仓" open={open} onCancel={onClose} width={640}
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
      ]} />

      {funds.length > 0 && (
        <div style={{ marginTop: 16 }}>
          <Table dataSource={funds} rowKey={(_, i) => String(i)} pagination={false} size="small"
            columns={[
              {
                title: '', width: 40,
                render: (_: any, __: any, i: number) => (
                  <Checkbox checked={selected.has(i)} onChange={e => {
                    const next = new Set(selected);
                    e.target.checked ? next.add(i) : next.delete(i);
                    setSelected(next);
                  }} />
                ),
              },
              { title: '基金名称', dataIndex: 'fund_name', key: 'name' },
              { title: '代码', dataIndex: 'fund_code', key: 'code', width: 80, render: (v: string) => v ? <Tag color="blue">{v}</Tag> : <Tag color="default">未匹配</Tag> },
              { title: '市值', dataIndex: 'current_value', key: 'val', render: (v: number) => `¥${v?.toLocaleString()}` },
              { title: '盈亏', dataIndex: 'current_profit', key: 'pl', render: (v: number) => (
                <span style={{ color: v >= 0 ? '#ff4d4f' : '#52c41a' }}>{v >= 0 ? '+' : ''}¥{v?.toLocaleString()}</span>
              )},
            ]} />
        </div>
      )}
    </Modal>
  );
};

export default SyncModal;
