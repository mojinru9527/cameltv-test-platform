import React from 'react';
import { Row, Col, Divider } from 'antd';
import {
  SafetyCertificateOutlined,
  ApiOutlined,
  PlaySquareOutlined,
  DatabaseOutlined,
} from '@ant-design/icons';
import TaskCard from '../components/TaskCard';
import TaskHistory from '../components/TaskHistory';
import { runEnvCheck, runApiTest, runUiAuto, generateData } from '../services/api';

interface Props {
  env: string;
}

const Dashboard: React.FC<Props> = ({ env }) => (
  <div>
    <Row gutter={[16, 16]}>
      <Col span={12}>
        <TaskCard
          title="环境健康检查"
          description="探测 DB/Redis/MQ/HTTP 连通性，输出红绿灯"
          icon={<SafetyCertificateOutlined />}
          env={env}
          onRun={() => runEnvCheck(env)}
        />
      </Col>
      <Col span={12}>
        <TaskCard
          title="API 回归测试"
          description="运行 Playwright MCP 接口自动化（swagger 优先）"
          icon={<ApiOutlined />}
          env={env}
          onRun={() => runApiTest(env)}
        />
      </Col>
      <Col span={12}>
        <TaskCard
          title="UI 自动化"
          description="midscene.js AI 驱动 UI 测试，覆盖 P0 功能用例"
          icon={<PlaySquareOutlined />}
          env={env}
          onRun={() => runUiAuto(env)}
        />
      </Col>
      <Col span={12}>
        <TaskCard
          title="测试数据生成"
          description="按模板生成关联测试数据并灌库"
          icon={<DatabaseOutlined />}
          env={env}
          onRun={() => generateData(env, 'vip_user', 10)}
        />
      </Col>
    </Row>
    <Divider>任务历史</Divider>
    <TaskHistory />
  </div>
);

export default Dashboard;
