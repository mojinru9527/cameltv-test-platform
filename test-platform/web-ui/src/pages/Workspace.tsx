import React from 'react';
import { Row, Col, Card, Statistic, Table, Tag, Button, Space, Divider, Progress } from 'antd';
import { useQuery } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import {
  CheckCircleOutlined,
  FileTextOutlined,
  ScheduleOutlined,
  PlayCircleOutlined,
  PlusOutlined,
  ApiOutlined,
} from '@ant-design/icons';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import { fetchWorkspaceStats } from '../services/api';

interface Props {
  env: string;
}

const Workspace: React.FC<Props> = ({ env }) => {
  const navigate = useNavigate();

  const { data, isLoading } = useQuery({
    queryKey: ['workspace-stats'],
    queryFn: fetchWorkspaceStats,
    refetchInterval: 30000,
  });

  const stats = data || {};
  const trend = stats.trend || [];
  const recentTasks = stats.recent_tasks || [];
  const modules = stats.modules || [];

  const statusColor: Record<string, string> = {
    passed: 'green', running: 'blue', failed: 'red', error: 'orange',
  };

  return (
    <div>
      {/* 统计卡片 */}
      <Row gutter={[16, 16]}>
        <Col span={6}>
          <Card>
            <Statistic
              title="用例总数"
              value={stats.total_cases || 0}
              prefix={<FileTextOutlined />}
              suffix={
                <span style={{ fontSize: 14, color: '#3f8600' }}>
                  已激活 {stats.active_cases || 0}
                </span>
              }
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="测试计划"
              value={stats.total_plans || 0}
              prefix={<ScheduleOutlined />}
              suffix={
                <span style={{ fontSize: 14, color: '#1677ff' }}>
                  活跃 {stats.active_plans || 0}
                </span>
              }
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="今日执行"
              value={stats.today_runs || 0}
              prefix={<PlayCircleOutlined />}
              suffix="次"
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="最近通过率"
              value={trend.length > 0 ? trend[trend.length - 1].rate : 0}
              prefix={<CheckCircleOutlined />}
              suffix="%"
              precision={1}
              valueStyle={{
                color: (trend.length > 0 && trend[trend.length - 1].rate >= 90)
                  ? '#3f8600' : '#cf1322',
              }}
            />
          </Card>
        </Col>
      </Row>

      <Divider />

      {/* 通过率趋势图 + 快捷入口 */}
      <Row gutter={[16, 16]}>
        <Col span={16}>
          <Card title="近 7 天执行通过率趋势">
            <ResponsiveContainer width="100%" height={280}>
              <LineChart data={trend}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="day" />
                <YAxis domain={[0, 100]} />
                <Tooltip formatter={(value: number) => `${value}%`} />
                <Line
                  type="monotone"
                  dataKey="rate"
                  stroke="#1677ff"
                  strokeWidth={2}
                  name="通过率 %"
                />
              </LineChart>
            </ResponsiveContainer>
          </Card>
        </Col>
        <Col span={8}>
          <Card title="快捷入口">
            <Space direction="vertical" style={{ width: '100%' }} size="middle">
              <Button
                type="primary"
                icon={<PlusOutlined />}
                block
                onClick={() => navigate('/test-cases')}
              >
                新建测试用例
              </Button>
              <Button
                icon={<ScheduleOutlined />}
                block
                onClick={() => navigate('/test-plans')}
              >
                创建测试计划
              </Button>
              <Button
                icon={<ApiOutlined />}
                block
                onClick={() => navigate('/api-testing')}
              >
                运行接口测试
              </Button>
            </Space>

            <Divider style={{ margin: '12px 0' }} />

            {/* 模块分布 */}
            <div style={{ fontSize: 13, color: '#666' }}>用例模块分布</div>
            {modules.slice(0, 6).map((m: any) => (
              <div key={m.module} style={{ marginTop: 8 }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 12 }}>
                  <span>{m.module}</span>
                  <span>{m.count}</span>
                </div>
                <Progress
                  percent={Math.round((m.count / Math.max(stats.total_cases || 1, 1)) * 100)}
                  size="small"
                  showInfo={false}
                />
              </div>
            ))}
            {modules.length === 0 && (
              <div style={{ color: '#999', fontSize: 12, textAlign: 'center', padding: 16 }}>
                暂无数据，请先创建测试用例
              </div>
            )}
          </Card>
        </Col>
      </Row>

      <Divider>最近任务</Divider>

      {/* 最近任务列表 */}
      <Table
        dataSource={recentTasks}
        columns={[
          { title: 'ID', dataIndex: 'id', width: 60 },
          { title: '类型', dataIndex: 'task_type', width: 100 },
          { title: '环境', dataIndex: 'env', width: 60 },
          {
            title: '状态', dataIndex: 'status', width: 80,
            render: (s: string) => <Tag color={statusColor[s] || 'default'}>{s}</Tag>,
          },
          { title: '开始时间', dataIndex: 'started_at', width: 160 },
          { title: '结果', dataIndex: 'result_summary', ellipsis: true },
        ]}
        rowKey="id"
        loading={isLoading}
        size="small"
        pagination={{ pageSize: 10 }}
        locale={{ emptyText: '暂无执行记录' }}
      />
    </div>
  );
};

export default Workspace;
