import React, { useEffect, useState } from 'react';
import { Card, Descriptions, Tag, Divider, Table, Typography } from 'antd';
import {
  UserOutlined, SettingOutlined, KeyOutlined, InfoCircleOutlined,
} from '@ant-design/icons';
import { fetchConfig } from '../services/api';

const { Text, Title } = Typography;

const Profile: React.FC = () => {
  const [configInfo, setConfigInfo] = useState<any>(null);

  useEffect(() => {
    fetchConfig().then(setConfigInfo).catch(() => {});
  }, []);

  // proxy_strategy 可能是对象(env→strategy)或字符串，统一处理
  const renderProxyStrategy = (val: any) => {
    if (!val) return <Tag>未知</Tag>;
    if (typeof val === 'string') {
      return <Tag color={val === 'vpn07' ? 'red' : 'green'}>{val}</Tag>;
    }
    if (typeof val === 'object') {
      return (
        <>
          {Object.entries(val).map(([env, strategy]) => (
            <Tag key={env} color={strategy === 'vpn07' ? 'red' : 'green'}>
              {env}: {strategy as string}
            </Tag>
          ))}
        </>
      );
    }
    return <Tag>未知</Tag>;
  };

  return (
    <div>
      <Title level={4}>
        <UserOutlined style={{ marginRight: 8 }} />
        个人中心
      </Title>

      {/* 平台信息 */}
      <Card title={<><InfoCircleOutlined /> 平台版本</>} style={{ marginBottom: 16 }}>
        <Descriptions size="small" column={2}>
          <Descriptions.Item label="平台名称">CamelTv 测试平台</Descriptions.Item>
          <Descriptions.Item label="版本号">0.3.0</Descriptions.Item>
          <Descriptions.Item label="前端框架">React 18 + Ant Design 5 + Vite 5</Descriptions.Item>
          <Descriptions.Item label="后端框架">FastAPI + SQLite</Descriptions.Item>
          <Descriptions.Item label="测试引擎">Playwright + midscene.js</Descriptions.Item>
          <Descriptions.Item label="部署方式">Docker Compose / Git Clone</Descriptions.Item>
        </Descriptions>
      </Card>

      {/* 项目配置 */}
      <Card title={<><SettingOutlined /> 项目配置</>} style={{ marginBottom: 16 }}>
        {configInfo ? (
          <Descriptions size="small" column={2}>
            <Descriptions.Item label="项目名称">{configInfo.project}</Descriptions.Item>
            <Descriptions.Item label="版本">{configInfo.version}</Descriptions.Item>
            <Descriptions.Item label="环境列表">
              {(configInfo.environments || []).map((e: string) => (
                <Tag key={e} color={e === 'prod' ? 'red' : 'green'}>{e}</Tag>
              ))}
            </Descriptions.Item>
            <Descriptions.Item label="当前环境">{configInfo.current_env || '-'}</Descriptions.Item>
            <Descriptions.Item label="Base URL" span={2}>
              <Text code>{configInfo.base_url || '-'}</Text>
            </Descriptions.Item>
            <Descriptions.Item label="代理策略" span={2}>
              {renderProxyStrategy(configInfo.proxy_strategy)}
            </Descriptions.Item>
          </Descriptions>
        ) : (
          <Text type="secondary">正在加载配置...</Text>
        )}
      </Card>

      {/* API Token 管理（占位） */}
      <Card title={<><KeyOutlined /> API Token</>} style={{ marginBottom: 16 }}>
        <Table
          dataSource={[
            { name: 'CAMELTV_PROD_AUTH_TOKEN', status: '未配置', env: '.env' },
            { name: 'CAMELTV_TEST_AUTH_TOKEN', status: '未配置', env: '.env' },
          ]}
          columns={[
            { title: 'Token 名称', dataIndex: 'name', ellipsis: true },
            { title: '状态', dataIndex: 'status', width: 100, render: (v: string) => <Tag color={v === '已配置' ? 'green' : 'orange'}>{v}</Tag> },
            { title: '配置位置', dataIndex: 'env', width: 100 },
          ]}
          rowKey="name"
          size="small"
          pagination={false}
        />
        <Divider style={{ margin: '12px 0' }} />
        <Text type="secondary" style={{ fontSize: 12 }}>
          提示：Token 配置在项目根目录的 <Text code>.env</Text> 文件中，服务器启动时自动加载。
        </Text>
      </Card>
    </div>
  );
};

export default Profile;
