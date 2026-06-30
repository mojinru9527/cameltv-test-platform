import React, { useState } from 'react';
import { Card, Button, Space, Tag, Result, Spin } from 'antd';
import { PlayCircleOutlined, CheckCircleOutlined, CloseCircleOutlined } from '@ant-design/icons';

interface Props {
  title: string;
  description: string;
  icon: React.ReactNode;
  env: string;
  onRun: () => Promise<{ status: string; message?: string }>;
}

const TaskCard: React.FC<Props> = ({ title, description, icon, env, onRun }) => {
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<'idle' | 'success' | 'error'>('idle');
  const [message, setMessage] = useState('');

  const handleRun = async () => {
    setLoading(true);
    setResult('idle');
    try {
      const res = await onRun();
      if (res.status === 'passed' || res.status === 'ok') {
        setResult('success');
        setMessage(res.message || '执行成功');
      } else {
        setResult('error');
        setMessage(res.message || '执行失败');
      }
    } catch (e: any) {
      setResult('error');
      setMessage(e.message || '请求失败');
    } finally {
      setLoading(false);
    }
  };

  return (
    <Card
      title={
        <Space>
          {icon}
          {title}
          <Tag>{env}</Tag>
        </Space>
      }
      extra={
        <Button
          type="primary"
          icon={<PlayCircleOutlined />}
          onClick={handleRun}
          loading={loading}
        >
          运行
        </Button>
      }
    >
      <p style={{ color: '#666' }}>{description}</p>
      {loading && <Spin tip="运行中..." />}
      {result === 'success' && (
        <Result
          status="success"
          title="执行成功"
          subTitle={message}
          style={{ padding: 16 }}
        />
      )}
      {result === 'error' && (
        <Result
          status="error"
          title="执行失败"
          subTitle={message}
          style={{ padding: 16 }}
        />
      )}
    </Card>
  );
};

export default TaskCard;
