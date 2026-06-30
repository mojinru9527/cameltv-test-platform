import React, { useState } from 'react';
import {
  Card, Table, Button, Space, Tag, Modal, Input, Select, Transfer,
  message, Popconfirm, Row, Col,
} from 'antd';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  PlusOutlined, PlayCircleOutlined, DeleteOutlined,
  ReloadOutlined, EditOutlined, EyeOutlined,
} from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import {
  fetchTestPlans, fetchTestCases, fetchTestPlan,
  createTestPlan, updateTestPlan,
  deleteTestPlan, runTestPlan,
} from '../services/api';

const TestPlans: React.FC = () => {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [modalOpen, setModalOpen] = useState(false);
  const [editingPlan, setEditingPlan] = useState<any>(null);

  // 查询
  const { data: planData, isLoading } = useQuery({
    queryKey: ['test-plans'],
    queryFn: () => fetchTestPlans(),
  });

  const { data: caseData } = useQuery({
    queryKey: ['test-cases-all'],
    queryFn: () => fetchTestCases({ limit: 500 }),
  });

  const plans = planData?.plans || [];
  const allCases = caseData?.cases || [];

  // 新建/编辑表单状态
  const [formName, setFormName] = useState('');
  const [formDesc, setFormDesc] = useState('');
  const [formEnv, setFormEnv] = useState('test');
  const [formCaseIds, setFormCaseIds] = useState<string[]>([]);

  // Mutations
  const saveMutation = useMutation({
    mutationFn: (values: any) =>
      editingPlan?.id
        ? updateTestPlan(editingPlan.id, values)
        : createTestPlan(values),
    onSuccess: () => {
      message.success(editingPlan?.id ? '计划已更新' : '计划已创建');
      setModalOpen(false);
      resetForm();
      queryClient.invalidateQueries({ queryKey: ['test-plans'] });
      queryClient.invalidateQueries({ queryKey: ['workspace-stats'] });
    },
  });

  const deleteMutation = useMutation({
    mutationFn: deleteTestPlan,
    onSuccess: () => {
      message.success('计划已删除');
      queryClient.invalidateQueries({ queryKey: ['test-plans'] });
      queryClient.invalidateQueries({ queryKey: ['workspace-stats'] });
    },
  });

  const runMutation = useMutation({
    mutationFn: runTestPlan,
    onSuccess: (data) => {
      message.info(`执行已启动 (run_id=${data.run_id})`);
      queryClient.invalidateQueries({ queryKey: ['test-plans'] });
      queryClient.invalidateQueries({ queryKey: ['workspace-stats'] });
    },
    onError: (e: any) => {
      message.error(e?.response?.data?.detail || '执行失败');
    },
  });

  const resetForm = () => {
    setFormName('');
    setFormDesc('');
    setFormEnv('test');
    setFormCaseIds([]);
    setEditingPlan(null);
  };

  const handleAdd = () => {
    resetForm();
    setModalOpen(true);
  };

  const handleEdit = (record: any) => {
    setEditingPlan(record);
    setFormName(record.name);
    setFormDesc(record.description || '');
    setFormEnv(record.env || 'test');
    // 需要加载计划详情获取关联的 case_ids
    setFormCaseIds([]);
    setModalOpen(true);
    // 异步加载关联用例
    fetchTestPlan(record.id).then((p) => {
      const ids = (p.items || []).map((it: any) => String(it.case_id));
      setFormCaseIds(ids);
    });
  };

  const handleSave = () => {
    if (!formName.trim()) {
      message.warning('请输入计划名称');
      return;
    }
    saveMutation.mutate({
      name: formName.trim(),
      description: formDesc,
      env: formEnv,
      case_ids: formCaseIds.map(Number),
    });
  };

  // Transfer 数据
  const transferData = allCases.map((c: any) => ({
    key: String(c.id),
    title: c.title,
    description: `${c.module || '-'} · ${c.priority}`,
  }));

  // 列定义
  const columns = [
    {
      title: '计划名称', dataIndex: 'name', ellipsis: true,
      render: (v: string, r: any) => (
        <a onClick={() => navigate(`/test-plans/${r.id}`)}>{v}</a>
      ),
    },
    { title: '描述', dataIndex: 'description', ellipsis: true, width: 200 },
    {
      title: '环境', dataIndex: 'env', width: 80,
      render: (v: string) => <Tag color={v === 'prod' ? 'red' : 'green'}>{v}</Tag>,
    },
    {
      title: '状态', dataIndex: 'status', width: 80,
      render: (v: string) => {
        const m: Record<string, { color: string; label: string }> = {
          draft: { color: 'default', label: '草稿' },
          active: { color: 'blue', label: '活跃' },
          completed: { color: 'green', label: '完成' },
        };
        return <Tag color={m[v]?.color}>{m[v]?.label || v}</Tag>;
      },
    },
    { title: '用例句数', dataIndex: 'case_count', width: 80 },
    {
      title: '通过率', dataIndex: 'pass_rate', width: 80,
      render: (v: number) => v != null ? `${v}%` : '-',
    },
    { title: '更新时间', dataIndex: 'updated_at', width: 160 },
    {
      title: '操作', key: 'actions', width: 220,
      render: (_: any, record: any) => (
        <Space>
          <Button
            size="small"
            icon={<EyeOutlined />}
            onClick={() => navigate(`/test-plans/${record.id}`)}
          >
            查看
          </Button>
          <Button
            size="small"
            icon={<EditOutlined />}
            onClick={() => handleEdit(record)}
          >
            编辑
          </Button>
          <Button
            size="small"
            type="primary"
            icon={<PlayCircleOutlined />}
            onClick={() => runMutation.mutate(record.id)}
            loading={runMutation.isPending}
          >
            执行
          </Button>
          <Popconfirm
            title="确定删除该计划？"
            onConfirm={() => deleteMutation.mutate(record.id)}
          >
            <Button size="small" danger icon={<DeleteOutlined />} />
          </Popconfirm>
        </Space>
      ),
    },
  ];

  return (
    <div>
      {/* 工具栏 */}
      <Card style={{ marginBottom: 16 }}>
        <Row justify="space-between" align="middle">
          <Col>
            <span style={{ fontSize: 16, fontWeight: 600 }}>测试计划列表</span>
          </Col>
          <Col>
            <Space>
              <Button
                icon={<ReloadOutlined />}
                onClick={() => queryClient.invalidateQueries({ queryKey: ['test-plans'] })}
              >
                刷新
              </Button>
              <Button type="primary" icon={<PlusOutlined />} onClick={handleAdd}>
                新建计划
              </Button>
            </Space>
          </Col>
        </Row>
      </Card>

      {/* 表格 */}
      <Table
        dataSource={plans}
        columns={columns}
        rowKey="id"
        loading={isLoading}
        size="small"
        pagination={{ pageSize: 20 }}
      />

      {/* 新建/编辑 Modal */}
      <Modal
        title={editingPlan?.id ? '编辑测试计划' : '新建测试计划'}
        open={modalOpen}
        onCancel={() => { setModalOpen(false); resetForm(); }}
        onOk={handleSave}
        confirmLoading={saveMutation.isPending}
        width={720}
        okText="保存"
        cancelText="取消"
      >
        <Space direction="vertical" style={{ width: '100%' }} size="middle">
          <div>
            <label style={{ fontWeight: 500 }}>计划名称 *</label>
            <Input
              value={formName}
              onChange={(e) => setFormName(e.target.value)}
              placeholder="例如: 首页接口回归测试"
            />
          </div>
          <div>
            <label style={{ fontWeight: 500 }}>描述</label>
            <Input.TextArea
              value={formDesc}
              onChange={(e) => setFormDesc(e.target.value)}
              rows={2}
              placeholder="描述计划目标与覆盖范围"
            />
          </div>
          <div>
            <label style={{ fontWeight: 500 }}>目标环境</label>
            <Select
              value={formEnv}
              onChange={setFormEnv}
              style={{ width: 120 }}
              options={[
                { value: 'test', label: '🧪 Test' },
                { value: 'prod', label: '🔒 Prod' },
              ]}
            />
          </div>
          <div>
            <label style={{ fontWeight: 500 }}>关联测试用例</label>
            <Transfer
              dataSource={transferData}
              targetKeys={formCaseIds}
              onChange={(keys) => setFormCaseIds(keys as string[])}
              render={(item) => item.title}
              listStyle={{ width: 280, height: 300 }}
              showSearch
              filterOption={(inputValue, item) =>
                item.title.toLowerCase().includes(inputValue.toLowerCase())
              }
              locale={{ itemUnit: '条', itemsUnit: '条', searchPlaceholder: '搜索用例' }}
            />
          </div>
        </Space>
      </Modal>
    </div>
  );
};

export default TestPlans;
