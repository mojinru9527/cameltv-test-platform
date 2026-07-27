import React, { useState } from 'react';
import {
  Card, Table, Button, Space, Tag, Drawer, Input, Select, Popconfirm,
  message, Row, Col, Tooltip,
} from 'antd';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  PlusOutlined, EditOutlined, DeleteOutlined, ImportOutlined,
  SearchOutlined, ReloadOutlined,
} from '@ant-design/icons';
import {
  fetchTestCases, fetchModules, createTestCase, updateTestCase,
  deleteTestCase, importAllTestCases,
} from '../services/api';

const priorityColor: Record<string, string> = {
  P0: 'red', P1: 'orange', P2: 'blue', P3: 'default',
};
const statusMap: Record<string, string> = {
  draft: '草稿', active: '激活', archived: '归档',
};
const typeMap: Record<string, string> = {
  api: 'API', ui: 'UI', manual: '手动',
};

const TestCases: React.FC = () => {
  const queryClient = useQueryClient();
  const [filters, setFilters] = useState({
    module: '', priority: '', status: '', type: '', keyword: '',
  });
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [editingCase, setEditingCase] = useState<any>(null);

  // 查询
  const { data, isLoading } = useQuery({
    queryKey: ['test-cases', filters],
    queryFn: () => fetchTestCases(filters),
  });

  const { data: moduleData } = useQuery({
    queryKey: ['modules'],
    queryFn: fetchModules,
  });

  const cases = data?.cases || [];
  const total = data?.total || 0;
  const modules = moduleData?.modules || [];

  // Mutations
  const saveMutation = useMutation({
    mutationFn: (values: any) =>
      editingCase?.id
        ? updateTestCase(editingCase.id, values)
        : createTestCase(values),
    onSuccess: () => {
      message.success(editingCase?.id ? '用例已更新' : '用例已创建');
      setDrawerOpen(false);
      setEditingCase(null);
      queryClient.invalidateQueries({ queryKey: ['test-cases'] });
      queryClient.invalidateQueries({ queryKey: ['modules'] });
      queryClient.invalidateQueries({ queryKey: ['workspace-stats'] });
    },
  });

  const deleteMutation = useMutation({
    mutationFn: deleteTestCase,
    onSuccess: () => {
      message.success('用例已删除');
      queryClient.invalidateQueries({ queryKey: ['test-cases'] });
      queryClient.invalidateQueries({ queryKey: ['workspace-stats'] });
    },
  });

  const importMutation = useMutation({
    mutationFn: importAllTestCases,
    onSuccess: (data) => {
      message.success(
        `功能用例 ${data.functional?.imported || 0} 条 + 接口用例 ${data.api_spec?.imported || 0} 条已导入` +
        (data.total_skipped ? `，跳过 ${data.total_skipped} 条已存在` : '')
      );
      queryClient.invalidateQueries({ queryKey: ['test-cases'] });
      queryClient.invalidateQueries({ queryKey: ['modules'] });
      queryClient.invalidateQueries({ queryKey: ['workspace-stats'] });
    },
    onError: (e: any) => {
      message.error(e?.response?.data?.detail || '导入失败');
    },
  });

  // 操作
  const handleAdd = () => {
    setEditingCase(null);
    setDrawerOpen(true);
  };

  const handleEdit = (record: any) => {
    setEditingCase(record);
    setDrawerOpen(true);
  };

  const handleSave = () => {
    // 表单数据由 Drawer 内部的受控组件收集
    const form = document.getElementById('case-form') as HTMLFormElement;
    if (!form) return;
    const fd = new FormData(form);
    const values: Record<string, any> = {};
    fd.forEach((v, k) => { values[k] = v; });

    // 处理 tags
    const tagsStr = values.tags as string || '';
    values.tags = tagsStr.split(',').map((t: string) => t.trim()).filter(Boolean);

    // 处理 steps（简单的 JSON 步骤编辑用 textarea）
    const stepsStr = values.steps as string || '';
    try {
      values.steps = JSON.parse(stepsStr);
    } catch {
      values.steps = stepsStr ? [{ step: 1, desc: stepsStr, expected: '' }] : [];
    }

    saveMutation.mutate(values);
  };

  // -------- 表单初始值 --------
  const formInitial = editingCase || {
    title: '', module: '', priority: 'P2', status: 'draft', type: 'api',
    tags: '', preconditions: '', steps: '', expected_result: '', api_spec_ref: '',
  };

  // -------- 列定义 --------
  const columns = [
    { title: 'ID', dataIndex: 'id', width: 60 },
    {
      title: '标题', dataIndex: 'title', ellipsis: true,
      render: (v: string, r: any) => (
        <Space>
          <span>{v}</span>
          {r.api_spec_ref && (
            <Tooltip title={`关联 API: ${r.api_spec_ref}`}>
              <Tag color="purple" style={{ fontSize: 10 }}>API</Tag>
            </Tooltip>
          )}
        </Space>
      ),
    },
    { title: '模块', dataIndex: 'module', width: 100, render: (v: string) => v ? <Tag>{v}</Tag> : '-' },
    {
      title: '优先级', dataIndex: 'priority', width: 80,
      render: (v: string) => <Tag color={priorityColor[v] || 'default'}>{v}</Tag>,
    },
    {
      title: '状态', dataIndex: 'status', width: 80,
      render: (v: string) => <Tag>{statusMap[v] || v}</Tag>,
    },
    {
      title: '类型', dataIndex: 'type', width: 70,
      render: (v: string) => <Tag>{typeMap[v] || v}</Tag>,
    },
    { title: '更新时间', dataIndex: 'updated_at', width: 160 },
    {
      title: '操作', key: 'actions', width: 140,
      render: (_: any, record: any) => (
        <Space>
          <Button size="small" icon={<EditOutlined />} onClick={() => handleEdit(record)}>
            编辑
          </Button>
          <Popconfirm
            title="确定删除该用例？"
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
        <Row gutter={[12, 12]} align="middle">
          <Col flex="auto">
            <Space wrap>
              <Input
                placeholder="关键词搜索"
                prefix={<SearchOutlined />}
                style={{ width: 180 }}
                value={filters.keyword}
                onChange={(e) => setFilters({ ...filters, keyword: e.target.value })}
                allowClear
              />
              <Select
                placeholder="模块"
                style={{ width: 120 }}
                value={filters.module || undefined}
                onChange={(v) => setFilters({ ...filters, module: v || '' })}
                allowClear
                options={modules.map((m: string) => ({ value: m, label: m }))}
              />
              <Select
                placeholder="优先级"
                style={{ width: 100 }}
                value={filters.priority || undefined}
                onChange={(v) => setFilters({ ...filters, priority: v || '' })}
                allowClear
                options={['P0', 'P1', 'P2', 'P3'].map(p => ({ value: p, label: p }))}
              />
              <Select
                placeholder="状态"
                style={{ width: 100 }}
                value={filters.status || undefined}
                onChange={(v) => setFilters({ ...filters, status: v || '' })}
                allowClear
                options={[
                  { value: 'draft', label: '草稿' },
                  { value: 'active', label: '激活' },
                  { value: 'archived', label: '归档' },
                ]}
              />
              <Select
                placeholder="类型"
                style={{ width: 100 }}
                value={filters.type || undefined}
                onChange={(v) => setFilters({ ...filters, type: v || '' })}
                allowClear
                options={[
                  { value: 'api', label: 'API' },
                  { value: 'ui', label: 'UI' },
                  { value: 'manual', label: '手动' },
                ]}
              />
              <Button
                icon={<ReloadOutlined />}
                onClick={() => queryClient.invalidateQueries({ queryKey: ['test-cases'] })}
              >
                刷新
              </Button>
            </Space>
          </Col>
          <Col>
            <Space>
              <Button
                icon={<ImportOutlined />}
                onClick={() => importMutation.mutate()}
                loading={importMutation.isPending}
              >
                导入全部用例
              </Button>
              <Button type="primary" icon={<PlusOutlined />} onClick={handleAdd}>
                新建用例
              </Button>
            </Space>
          </Col>
        </Row>
      </Card>

      {/* 表格 */}
      <Table
        dataSource={cases}
        columns={columns}
        rowKey="id"
        loading={isLoading}
        size="small"
        pagination={{ total, pageSize: 20, showTotal: (t) => `共 ${t} 条` }}
      />

      {/* 新建/编辑 Drawer */}
      <Drawer
        title={editingCase?.id ? '编辑测试用例' : '新建测试用例'}
        width={560}
        open={drawerOpen}
        onClose={() => { setDrawerOpen(false); setEditingCase(null); }}
        extra={
          <Space>
            <Button onClick={() => { setDrawerOpen(false); setEditingCase(null); }}>取消</Button>
            <Button type="primary" onClick={handleSave} loading={saveMutation.isPending}>
              保存
            </Button>
          </Space>
        }
      >
        <form id="case-form" style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
          <div>
            <label style={{ fontWeight: 500 }}>标题 *</label>
            <Input name="title" defaultValue={formInitial.title} placeholder="用例标题" />
          </div>
          <Row gutter={12}>
            <Col span={12}>
              <label style={{ fontWeight: 500 }}>模块</label>
              <Select
                style={{ width: '100%' }}
                defaultValue={formInitial.module || undefined}
                options={modules.map((m: string) => ({ value: m, label: m }))}
                onChange={(v) => {
                  // 将 select 值写入 hidden input 使 FormData 可读
                  const el = document.getElementById('case-module-hidden') as HTMLInputElement;
                  if (el) el.value = v || '';
                }}
                placeholder="选择或输入"
              />
              <input type="hidden" name="module" id="case-module-hidden" defaultValue={formInitial.module} />
            </Col>
            <Col span={12}>
              <label style={{ fontWeight: 500 }}>优先级</label>
              <Select
                style={{ width: '100%' }}
                defaultValue={formInitial.priority}
                options={['P0', 'P1', 'P2', 'P3'].map(p => ({ value: p, label: p }))}
                onChange={(v) => {
                  const el = document.getElementById('case-priority-hidden') as HTMLInputElement;
                  if (el) el.value = v;
                }}
              />
              <input type="hidden" name="priority" id="case-priority-hidden" defaultValue={formInitial.priority} />
            </Col>
          </Row>
          <Row gutter={12}>
            <Col span={12}>
              <label style={{ fontWeight: 500 }}>状态</label>
              <Select
                style={{ width: '100%' }}
                defaultValue={formInitial.status}
                options={[
                  { value: 'draft', label: '草稿' },
                  { value: 'active', label: '激活' },
                  { value: 'archived', label: '归档' },
                ]}
                onChange={(v) => {
                  const el = document.getElementById('case-status-hidden') as HTMLInputElement;
                  if (el) el.value = v;
                }}
              />
              <input type="hidden" name="status" id="case-status-hidden" defaultValue={formInitial.status} />
            </Col>
            <Col span={12}>
              <label style={{ fontWeight: 500 }}>类型</label>
              <Select
                style={{ width: '100%' }}
                defaultValue={formInitial.type}
                options={[
                  { value: 'api', label: 'API 接口' },
                  { value: 'ui', label: 'UI 界面' },
                  { value: 'manual', label: '手动用例' },
                ]}
                onChange={(v) => {
                  const el = document.getElementById('case-type-hidden') as HTMLInputElement;
                  if (el) el.value = v;
                }}
              />
              <input type="hidden" name="type" id="case-type-hidden" defaultValue={formInitial.type} />
            </Col>
          </Row>
          <div>
            <label style={{ fontWeight: 500 }}>标签（逗号分隔）</label>
            <Input
              name="tags"
              defaultValue={Array.isArray(formInitial.tags) ? formInitial.tags.join(', ') : formInitial.tags}
              placeholder="例如: 登录, 核心流程, P0"
            />
          </div>
          <div>
            <label style={{ fontWeight: 500 }}>前置条件</label>
            <Input.TextArea name="preconditions" defaultValue={formInitial.preconditions} rows={2} placeholder="例如: 用户已登录" />
          </div>
          <div>
            <label style={{ fontWeight: 500 }}>测试步骤 (JSON 格式)</label>
            <Input.TextArea
              name="steps"
              defaultValue={
                Array.isArray(formInitial.steps)
                  ? JSON.stringify(formInitial.steps, null, 2)
                  : formInitial.steps
              }
              rows={4}
              placeholder='例如: [{"step":1,"desc":"发送POST请求","expected":"返回200"}]'
            />
          </div>
          <div>
            <label style={{ fontWeight: 500 }}>预期结果</label>
            <Input.TextArea name="expected_result" defaultValue={formInitial.expected_result} rows={2} placeholder="描述用例的预期结果" />
          </div>
          <div>
            <label style={{ fontWeight: 500 }}>关联 API Spec</label>
            <Input name="api_spec_ref" defaultValue={formInitial.api_spec_ref} placeholder="例如: POST /account-service/login/anonymous/web" />
          </div>
        </form>
      </Drawer>
    </div>
  );
};

export default TestCases;
