import React, { useState } from 'react';
import { Card, Button, Alert, Divider, Table, Tag } from 'antd';
import { PlayCircleOutlined } from '@ant-design/icons';
import { runUiAuto, fetchReports } from '../services/api';
import { useQuery } from '@tanstack/react-query';

interface Props {
  env: string;
}

const UiAutomation: React.FC<Props> = ({ env }) => {
  const [running, setRunning] = useState(false);
  const [result, setResult] = useState<any>(null);

  const { data: reports } = useQuery({
    queryKey: ['reports-ui'],
    queryFn: () => fetchReports(20),
    refetchInterval: 15000,
  });

  const handleRun = async () => {
    setRunning(true);
    setResult(null);
    try {
      const res = await runUiAuto(env);
      setResult(res);
    } finally {
      setRunning(false);
    }
  };

  return (
    <div>
      <Card title={`UI 自动化 · ${env}`}>
        <p>基于 midscene.js AI 驱动, 覆盖 P0 功能用例。测试运行在 <Tag>{env}</Tag> 环境。</p>
        <Button
          type="primary"
          size="large"
          icon={<PlayCircleOutlined />}
          onClick={handleRun}
          loading={running}
        >
          运行 UI 自动化
        </Button>

        {result && (
          <Alert
            style={{ marginTop: 16 }}
            type={result.status === 'passed' ? 'success' : 'error'}
            message={`状态: ${result.status}`}
            description={result.message}
          />
        )}
      </Card>

      <Divider>UI 测试报告历史</Divider>
      <Table
        dataSource={(reports?.reports || []).filter((r: any) => r.source === 'ui')}
        columns={[
          { title: '#', dataIndex: 'run_id', width: 60 },
          { title: 'Build', dataIndex: 'build', width: 80 },
          { title: 'Total', dataIndex: 'total', width: 60 },
          { title: 'Passed', dataIndex: 'passed', width: 60 },
          { title: 'Failed', dataIndex: 'failed', width: 60 },
          { title: 'Pass Rate', dataIndex: 'pass_rate', width: 80, render: (v: number) => <Tag color={v >= 90 ? 'green' : 'red'}>{v}%</Tag> },
          { title: 'Time', dataIndex: 'ts' },
        ]}
        rowKey="run_id"
        size="small"
        pagination={{ pageSize: 10 }}
      />
    </div>
  );
};

export default UiAutomation;
