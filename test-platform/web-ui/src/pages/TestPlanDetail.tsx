import React, { useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  Card, Table, Tag, Button, Space, Descriptions, Divider,
  message, Result, Spin, Popconfirm, Select,
} from 'antd';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  ArrowLeftOutlined, PlayCircleOutlined, ReloadOutlined,
  CheckCircleOutlined, CloseCircleOutlined, MinusCircleOutlined,
} from '@ant-design/icons';
import {
  fetchTestPlan, runTestPlan, updateTestPlan, fetchTestCases,
} from '../services/api';

const itemStatusMap: Record<string, { color: string; icon: React.ReactNode }> = {
  pending: { color: 'default', icon: <MinusCircleOutlined /> },
  pass: { color: 'green', icon: <CheckCircleOutlined /> },
  fail: { color: 'red', icon: <CloseCircleOutlined /> },
  skip: { color: 'orange', icon: <MinusCircleOutlined /> },
};

const TestPlanDetail: React.FC = () => {
  const { planId } = useParams<{ planId: string }>();
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  const { data: plan, isLoading, refetch } = useQuery({
    queryKey: ['test-plan', planId],
    queryFn: () => fetchTestPlan(Number(planId)),
    enabled: !!planId,
    refetchInterval: 5000,  // 执行期间自动刷新
  });

  const runMutation = useMutation({
    mutationFn: () => runTestPlan(Number(planId)),
    onSuccess: (data) => {
      message.info(`执行已启动 (run_id=${data.run_id})`);
      refetch();
    },
    onError: (e: any) => {
      message.error(e?.response?.data?.detail || '执行失败');
    },
  });

  if (isLoading) return <Spin size="large" style={{ display: 'block', margin: '100px auto' }} />;
  if (!plan) return <Result status="404" title="计划不存在" />;

  const items = plan.items || [];
  const runs = plan.runs || [];

  return (
    <div>
      {/* 面包屑 */}
      <Space style={{ marginBottom: 16 }}>
        <Button icon={<ArrowLeftOutlined />} onClick={() => navigate('/test-plans')}>
          返回计划列表
        </Button>
      </Space>

      {/* 计划信息 */}
      <Card
        title={plan.name}
        extra={
          <Space>
            <Button icon={<ReloadOutlined />} onClick={() => refetch()}>刷新</Button>
            <Button
              type="primary"
              icon={<PlayCircleOutlined />}
              onClick={() => runMutation.mutate()}
              loading={runMutation.isPending}
            >
              执行全部
            </Button>
          </Space>
        }
        style={{ marginBottom: 16 }}
      >
        <Descriptions size="small" column={4}>
          <Descriptions.Item label="状态">
            <Tag color={plan.status === 'active' ? 'blue' : plan.status === 'completed' ? 'green' : 'default'}>
              {{ draft: '草稿', active: '活跃', completed: '完成' }[plan.status] || plan.status}
            </Tag>
          </Descriptions.Item>
          <Descriptions.Item label="环境">
            <Tag color={plan.env === 'prod' ? 'red' : 'green'}>{plan.env}</Tag>
          </Descriptions.Item>
          <Descriptions.Item label="用例句数">{items.length}</Descriptions.Item>
          <Descriptions.Item label="通过率">{plan.pass_rate != null ? `${plan.pass_rate}%` : '-'}</Descriptions.Item>
          <Descriptions.Item label="描述" span={4}>{plan.description || '-'}</Descriptions.Item>
        </Descriptions>
      </Card>

      {/* 关联用例列表 */}
      <Card title="关联用例" style={{ marginBottom: 16 }}>
        <Table
          dataSource={items}
          columns={[
            { title: '#', dataIndex: 'sort_order', width: 50, render: (_: any, __: any, i: number) => i + 1 },
            { title: '用例标题', dataIndex: 'case_title', ellipsis: true },
            { title: '模块', dataIndex: 'case_module', width: 100, render: (v: string) => v ? <Tag>{v}</Tag> : '-' },
            {
              title: '优先级', dataIndex: 'case_priority', width: 70,
              render: (v: string) => <Tag color={{ P0: 'red', P1: 'orange', P2: 'blue', P3: 'default' }[v]}>{v}</Tag>,
            },
            { title: '类型', dataIndex: 'case_type', width: 70, render: (v: string) => <Tag>{v}</Tag> },
            {
              title: '执行状态', dataIndex: 'status', width: 100,
              render: (v: string) => (
                <Tag color={itemStatusMap[v]?.color}>{v}</Tag>
              ),
            },
            { title: '实际结果', dataIndex: 'actual_result', ellipsis: true, width: 200 },
            { title: '执行时间', dataIndex: 'executed_at', width: 160, render: (v: string) => v || '-' },
          ]}
          rowKey="id"
          size="small"
          pagination={false}
        />
      </Card>

      {/* 执行历史 */}
      <Card title="执行历史">
        <Table
          dataSource={runs}
          columns={[
            { title: 'Run ID', dataIndex: 'id', width: 70 },
            {
              title: '状态', dataIndex: 'status', width: 80,
              render: (v: string) => (
                <Tag color={v === 'passed' ? 'green' : v === 'running' ? 'blue' : 'red'}>
                  {v}
                </Tag>
              ),
            },
            { title: '开始时间', dataIndex: 'started_at', width: 160 },
            { title: '结束时间', dataIndex: 'finished_at', width: 160, render: (v: string) => v || '进行中...' },
            {
              title: '概要', dataIndex: 'summary', width: 200,
              render: (v: any) => {
                if (!v || typeof v !== 'object') return '-';
                const s = v;
                return `共${s.total || 0} / 通过${s.passed || 0} / 失败${s.failed || 0} / 跳过${s.skipped || 0}`;
              },
            },
          ]}
          rowKey="id"
          size="small"
          pagination={false}
          locale={{ emptyText: '暂无执行记录' }}
        />
      </Card>
    </div>
  );
};

export default TestPlanDetail;
