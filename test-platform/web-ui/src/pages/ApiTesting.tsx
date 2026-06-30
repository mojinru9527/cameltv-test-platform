import React, { useState } from 'react';
import { Card, Input, Button, Space, Table, Tag, Alert, Divider } from 'antd';
import { CloudDownloadOutlined, PlayCircleOutlined } from '@ant-design/icons';
import { pullSwagger, runApiTest, fetchReports } from '../services/api';
import { useQuery } from '@tanstack/react-query';

interface Props {
  env: string;
}

const ApiTesting: React.FC<Props> = ({ env }) => {
  const [swaggerUrl, setSwaggerUrl] = useState('');
  const [pulling, setPulling] = useState(false);
  const [running, setRunning] = useState(false);
  const [result, setResult] = useState<any>(null);

  const { data: reports } = useQuery({
    queryKey: ['reports'],
    queryFn: () => fetchReports(20),
    refetchInterval: 15000,
  });

  const handlePull = async () => {
    if (!swaggerUrl) return;
    setPulling(true);
    try {
      const res = await pullSwagger(swaggerUrl);
      console.log(res);
    } finally {
      setPulling(false);
    }
  };

  const handleRun = async () => {
    setRunning(true);
    setResult(null);
    try {
      const res = await runApiTest(env);
      setResult(res);
    } finally {
      setRunning(false);
    }
  };

  return (
    <div>
      <Card title="1. 拉取 Swagger 生成测试">
        <Space style={{ width: '100%' }}>
          <Input
            placeholder="Swagger/OpenAPI URL 或本地路径"
            value={swaggerUrl}
            onChange={(e) => setSwaggerUrl(e.target.value)}
            style={{ width: 400 }}
          />
          <Button
            type="primary"
            icon={<CloudDownloadOutlined />}
            onClick={handlePull}
            loading={pulling}
          >
            拉取并生成
          </Button>
        </Space>
      </Card>

      <br />
      <Card title={`2. 运行 API 测试 · ${env}`}>
        <Button
          type="primary"
          size="large"
          icon={<PlayCircleOutlined />}
          onClick={handleRun}
          loading={running}
          danger={result?.status === 'failed'}
        >
          运行全部 API 测试
        </Button>

        {result && (
          <Alert
            style={{ marginTop: 16 }}
            type={result.status === 'passed' ? 'success' : 'error'}
            message={`共 ${result.result?.total || '?'} 条, 通过 ${result.result?.passed || '?'} 条`}
            description={
              result.result?.failed_cases?.length > 0 && (
                <ul>
                  {result.result.failed_cases.slice(0, 10).map((c: any, i: number) => (
                    <li key={i}>
                      {c.name}
                      {c.elk_links?.map((link: string, j: number) => (
                        <a key={j} href={link} target="_blank" style={{ marginLeft: 8 }}>
                          📊 ELK
                        </a>
                      ))}
                    </li>
                  ))}
                </ul>
              )
            }
          />
        )}
      </Card>

      <Divider>API 测试报告历史</Divider>
      <Table
        dataSource={(reports?.reports || []).filter((r: any) => r.source === 'api')}
        columns={[
          { title: '#', dataIndex: 'run_id', width: 60 },
          { title: 'Build', dataIndex: 'build', width: 80 },
          { title: 'Total', dataIndex: 'total', width: 60 },
          { title: 'Passed', dataIndex: 'passed', width: 60 },
          { title: 'Failed', dataIndex: 'failed', width: 60 },
          { title: 'Pass Rate', dataIndex: 'pass_rate', width: 80, render: (v: number) => <Tag color={v >= 90 ? 'green' : 'red'}>{v}%</Tag> },
          { title: 'Time', dataIndex: 'ts', width: 160 },
        ]}
        rowKey="run_id"
        size="small"
        pagination={{ pageSize: 10 }}
      />
    </div>
  );
};

export default ApiTesting;
