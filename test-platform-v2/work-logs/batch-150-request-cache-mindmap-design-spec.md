# Batch 150 — Design Spec（请求缓存/防抖/退避 + mindmap）

> **Design (🎨)** | Date: 2026-08-11 | Status: 就绪

## 0. 技术体系确认
前端 React + axios + shadcn/ui；无新增依赖。

## 1. 缓存契约
| 项 | 值 |
|----|----|
| 缓存位置 | client 模块级 Map（会话级） |
| TTL | 60s（低频静态数据） |
| 失效 | `clearApiCache(prefix)`：登出/401 全清；环境/域 CRUD 清对应前缀 |
| 去重 | 相同 key 进行中请求共享 Promise |
| 安全 | 传 signal 时绕过缓存（保留 abort 语义） |

## 2. 防抖
- `useDebouncedValue(value, 300)`：输入停止 300ms 后才更新依赖值。
- 应用：缺陷搜索（fKeyword）。

## 3. 轮询退避
- 500ms 起步；连续空/失败翻倍；上限 30s；收到新指标立即复位 500ms。
- 实现：setTimeout 链（非 setInterval），cleanup 清理。

## 4. mindmap
| 项 | 前 | 后 |
|----|----|----|
| 数据源 | /test-cases?page_size=10000 | /test-cases/taxonomy（服务端聚合） |
| 叶子 | 用例标题 | 模块节点计数（count） |
| 筛选 | 客户端过滤 | surface/domain 过滤后仍保留计数 |
| 响应 | ~10MB | KB 级 |

## 5. 状态核对
| 组件 | Loading | Empty | Error |
|------|---------|-------|-------|
| 脑图 | skeleton | 「暂无测试用例」 | AsyncState error + 重试 |
| 搜索 | 防抖期无 loading | - | 既有错误态 |

## 6. 设计签核
结论：通过
