import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { Table, Tag } from 'antd';
import { fetchTaskHistory } from '../services/api';

const statusColor: Record<string, string> = {
  passed: 'green',
  running: 'blue',
  failed: 'red',
  error: 'orange',
};

const TaskHistory: React.FC = () => {
  const { data, isLoading } = useQuery({
    queryKey: ['task-history'],
    queryFn: () => fetchTaskHistory(50),
    refetchInterval: 10000,
  });

  const columns = [
    { title: 'ID', dataIndex: 'id', width: 60 },
    { title: '类型', dataIndex: 'task_type', width: 100 },
    { title: '环境', dataIndex: 'env', width: 60 },
    {
      title: '状态',
      dataIndex: 'status',
      width: 80,
      render: (s: string) => <Tag color={statusColor[s] || 'default'}>{s}</Tag>,
    },
    { title: '开始时间', dataIndex: 'started_at', width: 160 },
    { title: '结果', dataIndex: 'result_summary', ellipsis: true },
  ];

  return (
    <Table
      dataSource={data?.tasks || []}
      columns={columns}
      rowKey="id"
      loading={isLoading}
      size="small"
      pagination={{ pageSize: 10 }}
    />
  );
};

export default TaskHistory;
