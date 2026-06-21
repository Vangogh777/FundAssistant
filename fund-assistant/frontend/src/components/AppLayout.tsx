import React, { useState, useEffect } from 'react';
import { Layout, Menu, Button, Avatar, Dropdown, Typography, Switch, Space, Drawer } from 'antd';
import {
  DashboardOutlined,
  FundOutlined,
  RobotOutlined,
  StockOutlined,
  SettingOutlined,
  LogoutOutlined,
  SunOutlined,
  MoonOutlined,
  MenuFoldOutlined,
  MenuUnfoldOutlined,
  UserOutlined,
  MenuOutlined,
} from '@ant-design/icons';
import { Outlet, useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '@/hooks/useAuth';
import { useTheme } from '@/theme/useTheme';

const { Header, Sider, Content } = Layout;
const { Text } = Typography;

const menuItems = [
  { key: '/', icon: <DashboardOutlined />, label: '估值看板' },
  { key: '/portfolio', icon: <FundOutlined />, label: '持仓管理' },
  { key: '/analysis', icon: <RobotOutlined />, label: 'AI 分析' },
  { key: '/market', icon: <StockOutlined />, label: '市场行情' },
  { key: '/settings', icon: <SettingOutlined />, label: '设置' },
];

const AppLayout: React.FC = () => {
  const [collapsed, setCollapsed] = useState(false);
  const [isMobile, setIsMobile] = useState(false);
  const [mobileDrawerOpen, setMobileDrawerOpen] = useState(false);
  const navigate = useNavigate();
  const location = useLocation();
  const { user, logout } = useAuth();
  const { mode, toggleTheme } = useTheme();

  // 检测屏幕宽度
  useEffect(() => {
    const checkWidth = () => {
      const mobile = window.innerWidth < 768;
      setIsMobile(mobile);
      if (mobile) setCollapsed(true);
    };
    checkWidth();
    window.addEventListener('resize', checkWidth);
    return () => window.removeEventListener('resize', checkWidth);
  }, []);

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  const handleNav = (key: string) => {
    navigate(key);
    setMobileDrawerOpen(false);
  };

  const userMenuItems = [
    {
      key: 'profile',
      icon: <UserOutlined />,
      label: `${user?.username || '用户'} (${user?.email || ''})`,
      disabled: true,
    },
    { type: 'divider' as const },
    {
      key: 'logout',
      icon: <LogoutOutlined />,
      label: '退出登录',
      danger: true,
      onClick: handleLogout,
    },
  ];

  const siderBg = mode === 'light' ? '#ffffff' : '#0a1628';
  const borderClr = mode === 'light' ? '#f0f0f0' : '#1e3a5f';

  // 侧边菜单组件（Sider 和 Drawer 共用）
  const SideMenu = () => (
    <div style={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
      <div
        style={{
          height: 64,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          borderBottom: `1px solid ${borderClr}`,
          flexShrink: 0,
        }}
      >
        <Text strong style={{ fontSize: 18, whiteSpace: 'nowrap' }}>
          📈 基金助手
        </Text>
      </div>
      <Menu
        mode="inline"
        selectedKeys={[location.pathname]}
        items={menuItems}
        onClick={({ key }) => handleNav(key)}
        theme={mode === 'dark' ? 'dark' : 'light'}
        style={{ flex: 1, borderInlineEnd: 'none' }}
      />
    </div>
  );

  return (
    <Layout style={{ minHeight: '100vh' }}>
      {/* Desktop 侧边栏 */}
      {!isMobile && (
        <Sider
          trigger={null}
          collapsible
          collapsed={collapsed}
          theme={mode === 'dark' ? 'dark' : 'light'}
          breakpoint="lg"
          style={{ borderRight: `1px solid ${borderClr}` }}
        >
          <div
            style={{
              height: 64,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              borderBottom: `1px solid ${borderClr}`,
            }}
          >
            <Text strong style={{ fontSize: collapsed ? 22 : 18, whiteSpace: 'nowrap' }}>
              {collapsed ? '📈' : '📈 基金助手'}
            </Text>
          </div>
          <Menu
            mode="inline"
            selectedKeys={[location.pathname]}
            items={menuItems}
            onClick={({ key }) => navigate(key)}
            theme={mode === 'dark' ? 'dark' : 'light'}
          />
        </Sider>
      )}

      {/* Mobile 抽屉菜单 */}
      {isMobile && (
        <Drawer
          placement="left"
          open={mobileDrawerOpen}
          onClose={() => setMobileDrawerOpen(false)}
          width={220}
          styles={{
            body: { padding: 0 },
            header: { display: 'none' },
          }}
          style={{ background: siderBg }}
        >
          <SideMenu />
        </Drawer>
      )}

      <Layout>
        <Header
          style={{
            padding: isMobile ? '0 12px' : '0 24px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            borderBottom: `1px solid ${borderClr}`,
            height: 56,
            lineHeight: '56px',
          }}
        >
          <Space>
            {isMobile ? (
              <Button
                type="text"
                icon={<MenuOutlined />}
                onClick={() => setMobileDrawerOpen(true)}
              />
            ) : (
              <Button
                type="text"
                icon={collapsed ? <MenuUnfoldOutlined /> : <MenuFoldOutlined />}
                onClick={() => setCollapsed(!collapsed)}
              />
            )}
            {isMobile && (
              <Text strong style={{ fontSize: 16 }}>基金助手</Text>
            )}
          </Space>

          <Space size={isMobile ? 'small' : 'middle'}>
            <Switch
              checkedChildren={<MoonOutlined />}
              unCheckedChildren={<SunOutlined />}
              checked={mode === 'dark'}
              onChange={toggleTheme}
              size={isMobile ? 'small' : 'default'}
            />
            <Dropdown menu={{ items: userMenuItems }} placement="bottomRight">
              <Avatar
                size={isMobile ? 'small' : 'default'}
                style={{ backgroundColor: '#1677ff', cursor: 'pointer' }}
                icon={<UserOutlined />}
              />
            </Dropdown>
          </Space>
        </Header>

        <Content style={{ margin: isMobile ? 12 : 24, minHeight: 280 }}>
          <Outlet />
        </Content>
      </Layout>
    </Layout>
  );
};

export default AppLayout;
