/** API 服务层 — 封装对 FastAPI 后端的 HTTP 请求。 */
import axios from 'axios';

const api = axios.create({
  baseURL: '/api',
  timeout: 600000, // 10 分钟（长任务如 api run 需要）
});

// ═══════════════════════════════════════════════════════════════
// Workspace
// ═══════════════════════════════════════════════════════════════

export async function fetchWorkspaceStats() {
  const { data } = await api.get('/workspace/stats');
  return data;
}

// ═══════════════════════════════════════════════════════════════
// Test Cases
// ═══════════════════════════════════════════════════════════════

export async function fetchTestCases(params?: Record<string, any>) {
  const { data } = await api.get('/test-cases', { params });
  return data;
}

export async function fetchTestCase(id: number) {
  const { data } = await api.get(`/test-cases/${id}`);
  return data;
}

export async function createTestCase(body: Record<string, any>) {
  const { data } = await api.post('/test-cases', body);
  return data;
}

export async function updateTestCase(id: number, body: Record<string, any>) {
  const { data } = await api.put(`/test-cases/${id}`, body);
  return data;
}

export async function deleteTestCase(id: number) {
  const { data } = await api.delete(`/test-cases/${id}`);
  return data;
}

export async function fetchModules() {
  const { data } = await api.get('/test-cases/modules');
  return data;
}

export async function importTestCases(cases: Record<string, any>[]) {
  const { data } = await api.post('/test-cases/import', { cases });
  return data;
}

export async function importGeneratedTestCases() {
  const { data } = await api.post('/test-cases/import-generated');
  return data;
}

export async function importAllTestCases() {
  const { data } = await api.post('/test-cases/import-all');
  return data;
}

// ═══════════════════════════════════════════════════════════════
// Test Plans
// ═══════════════════════════════════════════════════════════════

export async function fetchTestPlans(params?: Record<string, any>) {
  const { data } = await api.get('/test-plans', { params });
  return data;
}

export async function fetchTestPlan(id: number) {
  const { data } = await api.get(`/test-plans/${id}`);
  return data;
}

export async function createTestPlan(body: Record<string, any>) {
  const { data } = await api.post('/test-plans', body);
  return data;
}

export async function updateTestPlan(id: number, body: Record<string, any>) {
  const { data } = await api.put(`/test-plans/${id}`, body);
  return data;
}

export async function deleteTestPlan(id: number) {
  const { data } = await api.delete(`/test-plans/${id}`);
  return data;
}

export async function runTestPlan(id: number) {
  const { data } = await api.post(`/test-plans/${id}/run`);
  return data;
}

// ═══════════════════════════════════════════════════════════════
// Config
// ═══════════════════════════════════════════════════════════════

export async function fetchConfig() {
  const { data } = await api.get('/config');
  return data;
}

export async function fetchConfigEnv(env: string) {
  const { data } = await api.get(`/config/${env}`);
  return data;
}

// ═══════════════════════════════════════════════════════════════
// Env Check
// ═══════════════════════════════════════════════════════════════

export async function runEnvCheck(env: string) {
  const { data } = await api.post('/envcheck', { env });
  return data;
}

// ═══════════════════════════════════════════════════════════════
// API Test
// ═══════════════════════════════════════════════════════════════

export async function runApiTest(env: string, filter = '') {
  const { data } = await api.post('/api-test/run', { env, filter });
  return data;
}

export async function pullSwagger(source: string) {
  const { data } = await api.post('/api-test/pull-swagger', { source });
  return data;
}

// ═══════════════════════════════════════════════════════════════
// UI Auto
// ═══════════════════════════════════════════════════════════════

export async function runUiAuto(env: string) {
  const { data } = await api.post('/ui-auto/run', { env });
  return data;
}

// ═══════════════════════════════════════════════════════════════
// Data Factory
// ═══════════════════════════════════════════════════════════════

export async function generateData(env: string, template: string, count = 10) {
  const { data } = await api.post('/datafactory/generate', { env, template, count });
  return data;
}

// ═══════════════════════════════════════════════════════════════
// Reports
// ═══════════════════════════════════════════════════════════════

export async function fetchReports(limit = 20) {
  const { data } = await api.get('/reports', { params: { limit } });
  return data;
}

// ═══════════════════════════════════════════════════════════════
// Task History
// ═══════════════════════════════════════════════════════════════

export async function fetchTaskHistory(limit = 50) {
  const { data } = await api.get('/task-history', { params: { limit } });
  return data;
}
