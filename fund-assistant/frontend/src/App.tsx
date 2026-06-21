import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { ConfigProvider, App as AntApp } from 'antd';
import zhCN from 'antd/locale/zh_CN';
import { AuthContext, useAuthProvider } from '@/hooks/useAuth';
import { useTheme } from '@/theme/useTheme';
import AppLayout from '@/components/AppLayout';
import Login from '@/pages/Login';
import Register from '@/pages/Register';
import Dashboard from '@/pages/Dashboard';
import Portfolio from '@/pages/Portfolio';
import Analysis from '@/pages/Analysis';
import Market from '@/pages/Market';
import Settings from '@/pages/Settings';

const App: React.FC = () => {
  const auth = useAuthProvider();
  const { theme } = useTheme();

  return (
    <ConfigProvider theme={theme} locale={zhCN}>
      <AntApp>
        <AuthContext.Provider value={auth}>
          <BrowserRouter>
            <Routes>
              {/* 公开路由 */}
              <Route
                path="/login"
                element={auth.isAuthenticated ? <Navigate to="/" replace /> : <Login />}
              />
              <Route
                path="/register"
                element={auth.isAuthenticated ? <Navigate to="/" replace /> : <Register />}
              />

              {/* 受保护路由 */}
              <Route
                path="/*"
                element={
                  auth.loading ? (
                    <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100vh' }}>
                      加载中...
                    </div>
                  ) : auth.isAuthenticated ? (
                    <AppLayout />
                  ) : (
                    <Navigate to="/login" replace />
                  )
                }
              >
                <Route index element={<Dashboard />} />
                <Route path="portfolio" element={<Portfolio />} />
                <Route path="analysis" element={<Analysis />} />
                <Route path="market" element={<Market />} />
                <Route path="settings" element={<Settings />} />
              </Route>
            </Routes>
          </BrowserRouter>
        </AuthContext.Provider>
      </AntApp>
    </ConfigProvider>
  );
};

export default App;
