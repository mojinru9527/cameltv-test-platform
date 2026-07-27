import React from 'react';
import { Select, Tag, Space } from 'antd';
import { SafetyOutlined } from '@ant-design/icons';

interface Props {
  env: string;
  onChange: (env: string) => void;
}

const envOptions = [
  { value: 'test', label: '🧪 Test', color: 'green' },
  { value: 'prod', label: '🔒 Prod', color: 'red' },
];

const EnvSelector: React.FC<Props> = ({ env, onChange }) => (
  <Space>
    <span>环境:</span>
    <Select
      value={env}
      onChange={onChange}
      style={{ width: 120 }}
      options={envOptions}
    />
    {env === 'test' ? (
      <Tag color="green">内网直连</Tag>
    ) : (
      <Tag color="red" icon={<SafetyOutlined />}>vpn07</Tag>
    )}
  </Space>
);

export default EnvSelector;
