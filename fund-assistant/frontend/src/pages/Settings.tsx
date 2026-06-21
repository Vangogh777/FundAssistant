import React, { useState, useEffect } from 'react';
import {
  Typography, Card, Tabs, Form, Input, Button, message,
  Table, Select, InputNumber, DatePicker, Space, Popconfirm, Tag, Switch
} from 'antd';
import {
  PlusOutlined, DeleteOutlined, RobotOutlined,
  MailOutlined, SendOutlined, WechatOutlined, QqOutlined
} from '@ant-design/icons';
import { fundApi } from '@/api/fund';
import { useAuth } from '@/hooks/useAuth';
import dayjs from 'dayjs';

const { Title, Text } = Typography;

// ====== API Keys 面板 ======
const ApiKeyPanel: React.FC = () => {
  const { user, updateUser } = useAuth();
  const [form] = Form.useForm();

  useEffect(() => {
    if (user) {
      form.setFieldsValue({
        openai: user.api_keys?.openai || '',
        deepseek: user.api_keys?.deepseek || '',
        claude: user.api_keys?.claude || '',
      });
    }
  }, [user]);

  const handleSave = async (values: Record<string, string>) => {
    const api_keys: Record<string, string> = {};
    if (values.openai) api_keys.openai = values.openai;
    if (values.deepseek) api_keys.deepseek = values.deepseek;
    if (values.claude) api_keys.claude = values.claude;
    await updateUser({ api_keys });
    message.success('API Keys 已保存');
  };

  return (
    <Card title={<span><RobotOutlined /> AI 模型 API Key 配置</span>}>
      <Text type="secondary" style={{ marginBottom: 16, display: 'block' }}>
        配置 API Key 即可在「AI 分析」中使用。同一提供商的 Key 可通用（如 DeepSeek 一个 Key 支持 Flash 和 Pro）。密钥仅保存在您的账户中。
      </Text>
      <Form form={form} onFinish={handleSave} layout="vertical">
        <Form.Item name="openai" label="OpenAI API Key">
          <Input.Password placeholder="sk-..." />
        </Form.Item>
        <Form.Item name="deepseek" label="DeepSeek API Key">
          <Input.Password placeholder="sk-..." />
        </Form.Item>
        <Form.Item name="claude" label="Claude API Key">
          <Input.Password placeholder="sk-ant-..." />
        </Form.Item>
        <Form.Item>
          <Button type="primary" htmlType="submit">保存</Button>
        </Form.Item>
      </Form>
    </Card>
  );
};

// ====== 通知渠道面板 ======
const NotifyPanel: React.FC = () => {
  const [channels, setChannels] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => { loadChannels(); }, []);

  const loadChannels = async () => {
    setLoading(true);
    try { const res = await fundApi.getChannels(); setChannels(res.data); } catch {}
    finally { setLoading(false); }
  };

  const addChannel = async (type: string) => {
    const configs: Record<string, any> = {
      email: { address: prompt('输入邮箱地址:') || '' },
      feishu: { webhook_url: prompt('输入飞书机器人 Webhook URL:') || '' },
      wechat: { server_chan_key: prompt('输入 ServerChan Key:') || '' },
      qq: { qq_number: prompt('输入 QQ 号:') || '' },
    };
    if (!Object.values(configs[type]).some(v => v)) return;
    try {
      await fundApi.createChannel({ channel_type: type, config: configs[type] });
      message.success('渠道添加成功');
      loadChannels();
    } catch { message.error('添加失败'); }
  };

  const deleteChannel = async (id: number) => {
    await fundApi.deleteChannel(id);
    message.success('删除成功');
    loadChannels();
  };

  const iconMap: Record<string, React.ReactNode> = {
    email: <MailOutlined />,
    feishu: <SendOutlined />,
    wechat: <WechatOutlined />,
    qq: <QqOutlined />,
  };

  const nameMap: Record<string, string> = {
    email: '邮件',
    feishu: '飞书机器人',
    wechat: '微信 (ServerChan)',
    qq: 'QQ 推送',
  };

  return (
    <Card title="📬 通知渠道">
      <Space wrap style={{ marginBottom: 16 }}>
        {(['email', 'feishu', 'wechat', 'qq'] as const).map(type => (
          <Button key={type} icon={iconMap[type]} onClick={() => addChannel(type)}>
            添加{nameMap[type]}
          </Button>
        ))}
      </Space>

      <Table
        dataSource={channels}
        rowKey="id"
        loading={loading}
        pagination={false}
        columns={[
          {
            title: '渠道',
            dataIndex: 'channel_type',
            key: 'type',
            render: (t: string) => <Tag icon={iconMap[t]}>{nameMap[t] || t}</Tag>,
          },
          {
            title: '配置',
            dataIndex: 'config',
            key: 'config',
            render: (c: Record<string, string>) => {
              const kv = Object.entries(c)[0];
              return <Text>{kv?.[0]}: {kv?.[1]?.slice(0, 30)}...</Text>;
            },
          },
          {
            title: '状态',
            dataIndex: 'is_active',
            key: 'active',
            render: (v: boolean) => v ? <Tag color="green">启用</Tag> : <Tag color="default">停用</Tag>,
          },
          {
            title: '操作',
            key: 'actions',
            render: (_: any, r: any) => (
              <Popconfirm title="确认删除？" onConfirm={() => deleteChannel(r.id)}>
                <Button type="link" danger icon={<DeleteOutlined />} />
              </Popconfirm>
            ),
          },
        ]}
        locale={{ emptyText: '暂无通知渠道' }}
      />
    </Card>
  );
};

// ====== 定投计划面板 ======
const DripPanel: React.FC = () => {
  const [plans, setPlans] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [form] = Form.useForm();

  useEffect(() => { loadPlans(); }, []);

  const loadPlans = async () => {
    setLoading(true);
    try { const res = await fundApi.getDripPlans(); setPlans(res.data); } catch {}
    finally { setLoading(false); }
  };

  const handleCreate = async (values: any) => {
    try {
      await fundApi.createDripPlan({
        ...values,
        next_run_date: values.next_run_date.format('YYYY-MM-DD'),
      });
      message.success('定投计划创建成功');
      form.resetFields();
      loadPlans();
    } catch { message.error('创建失败'); }
  };

  const deletePlan = async (id: number) => {
    await fundApi.deleteDripPlan(id);
    message.success('删除成功');
    loadPlans();
  };

  return (
    <Card title="⏰ 定投提醒">
      <Form form={form} onFinish={handleCreate} layout="inline" style={{ marginBottom: 16 }}>
        <Form.Item name="fund_code" rules={[{ required: true }]}>
          <Input placeholder="基金代码" style={{ width: 120 }} />
        </Form.Item>
        <Form.Item name="amount" rules={[{ required: true }]}>
          <InputNumber placeholder="每期金额" min={0} style={{ width: 140 }} prefix="¥" />
        </Form.Item>
        <Form.Item name="frequency" initialValue="monthly" rules={[{ required: true }]}>
          <Select style={{ width: 100 }}
            options={[
              { value: 'daily', label: '每天' },
              { value: 'weekly', label: '每周' },
              { value: 'biweekly', label: '双周' },
              { value: 'monthly', label: '每月' },
            ]}
          />
        </Form.Item>
        <Form.Item name="day_of_month" initialValue={1}>
          <InputNumber placeholder="日" min={1} max={28} style={{ width: 70 }} />
        </Form.Item>
        <Form.Item name="next_run_date" rules={[{ required: true }]}>
          <DatePicker placeholder="下次执行日" />
        </Form.Item>
        <Form.Item>
          <Button type="primary" htmlType="submit" icon={<PlusOutlined />}>创建</Button>
        </Form.Item>
      </Form>

      <Table
        dataSource={plans}
        rowKey="id"
        loading={loading}
        pagination={false}
        columns={[
          { title: '基金', dataIndex: 'fund_code', key: 'fund' },
          { title: '每期金额', dataIndex: 'amount', key: 'amt', render: (v: number) => `¥${v}` },
          {
            title: '频率', dataIndex: 'frequency', key: 'freq',
            render: (v: string) => {
              const m: Record<string, string> = { daily: '每天', weekly: '每周', biweekly: '双周', monthly: '每月' };
              return m[v] || v;
            },
          },
          { title: '下次执行', dataIndex: 'next_run_date', key: 'next' },
          {
            title: '状态', dataIndex: 'is_active', key: 'active',
            render: (v: boolean) => <Tag color={v ? 'green' : 'default'}>{v ? '运行中' : '已暂停'}</Tag>,
          },
          {
            title: '操作', key: 'actions',
            render: (_: any, r: any) => (
              <Popconfirm title="删除？" onConfirm={() => deletePlan(r.id)}>
                <Button type="link" danger icon={<DeleteOutlined />} />
              </Popconfirm>
            ),
          },
        ]}
        locale={{ emptyText: '暂无定投计划' }}
      />
    </Card>
  );
};

// ====== 设置主页 ======
const Settings: React.FC = () => {
  return (
    <div>
      <Title level={3}>⚙️ 设置</Title>
      <Tabs
        defaultActiveKey="api"
        items={[
          { key: 'api', label: <span><RobotOutlined /> AI 模型</span>, children: <ApiKeyPanel /> },
          { key: 'notify', label: '🔔 通知渠道', children: <NotifyPanel /> },
          { key: 'drip', label: '⏰ 定投计划', children: <DripPanel /> },
        ]}
      />
    </div>
  );
};

export default Settings;
