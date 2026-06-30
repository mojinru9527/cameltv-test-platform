import React from 'react';
import { Card, Table, Tag, Statistic, Row, Col, Divider } from 'antd';
import { useQuery } from '@tanstack/react-query';
import { fetchReports } from '../services/api';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';

interface Props {
  env: string;
}

const Reports: React.FC<Props> = ({ env }) => {
  const { data, isLoading } = useQuery({
    queryKey: ['reports-all'],
    queryFn: () => fetchReports(50),
    refetchInterval: 15000,
  });

  const reports = data?.reports || [];
  const latest = reports[0] || {};
  const chartData = reports.slice(0, 20).reverse().map((r: any) => ({
    build: r.build,
    passRate: r.pass_rate,
    total: r.total,
  }));

  return (
    <div>
      <Row gutter={[16, 16]}>
        <Col span={6}>
          <Card><Statistic title="总报告数" value={reports.length} /></Card>
        </Col>
        <Col span={6}>
          <Card><Statistic title="最新通过率" value={latest.pass_rate || 0} suffix="%" precision={1} /></Card>
        </Col>
        <Col span={6}>
          <Card><Statistic title="最新总数" value={latest.total || 0} /></Card>
        </Col>
        <Col span={6}>
          <Card><Statistic title="最新失败" value={latest.failed || 0} valueStyle={{ color: latest.failed > 0 ? '#cf1322' : '#3f8600' }} /></Card>
        </Col>
      </Row>

      <Divider>通过率趋势</Divider>
      <ResponsiveContainer width="100%" height={300}>
        <LineChart data={chartData}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis dataKey="build" />
          <YAxis domain={[0, 100]} />
          <Tooltip />
          <Line type="monotone" dataKey="passRate" stroke="#1677ff" name="通过率 %" />
        </LineChart>
      </ResponsiveContainer>

      <Divider>报告列表</Divider>
      <Table
        dataSource={reports}
        columns={[
          { title: '#', dataIndex: 'run_id', width: 60 },
          { title: '来源', dataIndex: 'source', width: 80, render: (v: string) => <Tag>{v}</Tag> },
          { title: 'Build', dataIndex: 'build', width: 80 },
          { title: 'Total', dataIndex: 'total', width: 60 },
          { title: 'Passed', dataIndex: 'passed', width: 60 },
          { title: 'Failed', dataIndex: 'failed', width: 60 },
          { title: '通过率', dataIndex: 'pass_rate', width: 80, render: (v: number) => <Tag color={v >= 90 ? 'green' : v >= 70 ? 'orange' : 'red'}>{v}%</Tag> },
          { title: '时间', dataIndex: 'ts', width: 160 },
        ]}
        rowKey="run_id"
        loading={isLoading}
        size="small"
        pagination={{ pageSize: 15 }}
      />
    </div>
  );
};

export default Reports;
