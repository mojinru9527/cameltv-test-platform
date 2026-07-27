import React, { useState } from 'react';
import { Routes, Route, useNavigate, useLocation } from 'react-router-dom';
import { Layout, Menu } from 'antd';
import {
  AppstoreOutlined,
  FileTextOutlined,
  ScheduleOutlined,
  ApiOutlined,
  BarChartOutlined,
  UserOutlined,
} from '@ant-design/icons';
import Workspace from './pages/Workspace';
import TestCases from './pages/TestCases';
import TestPlans from './pages/TestPlans';
import TestPlanDetail from './pages/TestPlanDetail';
import ApiTesting from './pages/ApiTesting';
import Reports from './pages/Reports';
import Profile from './pages/Profile';
import EnvSelector from './components/EnvSelector';

const { Header, Sider, Content } = Layout;

const menuItems = [
  { key: '/', icon: <AppstoreOutlined />, label: '工作台' },
  { key: '/test-cases', icon: <FileTextOutlined />, label: '测试用例' },
  { key: '/test-plans', icon: <ScheduleOutlined />, label: '测试计划' },
  { key: '/api-testing', icon: <ApiOutlined />, label: '接口测试' },
  { key: '/reports', icon: <BarChartOutlined />, label: '报告中心' },
  { key: '/profile', icon: <UserOutlined />, label: '个人中心' },
];

const App: React.FC = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const [env, setEnv] = useState<string>(() => localStorage.getItem('tp_env') || 'test');

  const handleEnvChange = (newEnv: string) => {
    setEnv(newEnv);
    localStorage.setItem('tp_env', newEnv);
  };

  // 选中菜单项：对于 /test-plans/:id 路径高亮 /test-plans
  const selectedKey = location.pathname.startsWith('/test-plans/')
    ? '/test-plans'
    : location.pathname;

  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Sider collapsible theme="dark">
        <div style={{ color: '#fff', textAlign: 'center', padding: '16px', fontWeight: 'bold', fontSize: 15 }}>
          🐪 CamelTv 测试平台
        </div>
        <Menu
          theme="dark"
          mode="inline"
          selectedKeys={[selectedKey]}
          items={menuItems}
          onClick={({ key }) => navigate(key)}
        />
      </Sider>
      <Layout>
        <Header style={{ background: '#fff', padding: '0 24px', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <h2 style={{ margin: 0 }}>
            {{ '/': '工作台', '/test-cases': '测试用例', '/test-plans': '测试计划',
               '/api-testing': '接口测试', '/reports': '报告中心', '/profile': '个人中心' }[selectedKey]
              || 'CamelTv 测试平台'}
          </h2>
          <EnvSelector env={env} onChange={handleEnvChange} />
        </Header>
        <Content style={{ margin: 16, padding: 24, background: '#fff', borderRadius: 8 }}>
          <Routes>
            <Route path="/" element={<Workspace env={env} />} />
            <Route path="/test-cases" element={<TestCases />} />
            <Route path="/test-plans" element={<TestPlans />} />
            <Route path="/test-plans/:planId" element={<TestPlanDetail />} />
            <Route path="/api-testing" element={<ApiTesting env={env} />} />
            <Route path="/reports" element={<Reports env={env} />} />
            <Route path="/profile" element={<Profile />} />
          </Routes>
        </Content>
      </Layout>
    </Layout>
  );
};

export default App;
