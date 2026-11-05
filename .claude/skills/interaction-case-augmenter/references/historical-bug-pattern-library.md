# Historical Bug Pattern Library — 未来娃屿（项目级生成记忆）

> 本文件是功能用例生成 Skill 的检索知识，**不是每轮都要执行的回归用例清单**。
> 机器检索唯一事实源：`historical-bug-pattern-library.json`；覆盖映射：`bug-pattern-coverage.csv`。
> 初始化数据来自真实缺陷登记与历史测试台账（2026-10~11），未编造任何 Bug。

## 统计

| 覆盖强度 | 数量 | 处理动作 |
|---|---:|---|
| strong | 6 | skip（不新增） |
| partial | 16 | enhance-existing（增强原用例） |
| none | 7 | add-minimal-case（仅适用时新增最小用例） |
| unknown | 0 | confirm（待确认） |

## 模式索引

| Pattern | 模式 | 来源 Bug | 覆盖强度 | 动作 | 既有用例 |
|---|---|---|---|---|---|
| CAMEL-BP-001 | 重复触发未防抖导致重复页面/重复业务结果 | REG-01, U1 | partial | enhance-existing | TC-MP-50-P, TC-MP-66-N |
| CAMEL-BP-002 | 同一字段在不同入口的长度/格式校验不一致 | REG-04, REG-20, REG-27, REG-31 | none | add-minimal-case |  |
| CAMEL-BP-003 | 超长/纯数字文本溢出、不换行、截断与遮挡 | REG-03, REG-12, REG-17, REG-19 | partial | enhance-existing | TC-MP-41-P |
| CAMEL-BP-004 | 抽屉/弹窗关闭后状态残留导致页面失效 | REG-25, REG-26, U25 | none | add-minimal-case |  |
| CAMEL-BP-005 | 搜索/筛选后行操作无响应或结果集不完整 | REG-24, REG-34 | partial | enhance-existing | TC-ADM-50-P, TC-ADM-03-P |
| CAMEL-BP-006 | 异步生成/渲染任务无进度、超时或结果不可重拉 | REG-05, REG-29, U5 | none | add-minimal-case |  |
| CAMEL-BP-007 | 不应出现的操作入口仍展示（关注/删除/购买） | REG-06, REG-07, REG-10, U6 | partial | enhance-existing | TC-MP-23-P, TC-MP-26-N |
| CAMEL-BP-008 | 空态/缺省资源无兜底（无图无头像占位文案） | REG-18, REG-32, U18 | partial | enhance-existing | TC-MP-63-P |
| CAMEL-BP-009 | 时间/时区展示漂移（相对时间错误） | REG-13, U13b | none | add-minimal-case |  |
| CAMEL-BP-010 | 图片上传无尺寸约束导致展示裁切 | REG-21, U21 | none | add-minimal-case |  |
| CAMEL-BP-011 | 地址/文本解析规则缺失（直辖市与重名市区） | REG-23, U23, U24 | partial | enhance-existing | TC-MP-06-P |
| CAMEL-BP-012 | 首次登录资料缺失导致主流程中断 | REG-02, U2 | partial | enhance-existing | TC-MP-02-P, TC-MP-04-P |
| CAMEL-BP-013 | 保存/草稿动作未触发或状态不持久 | REG-09, U10 | strong | skip | TC-MP-76-P |
| CAMEL-BP-014 | 社交关系数据不可查看/计数不一致 | REG-22, U22, D-20 | partial | enhance-existing | TC-MP-73-P |
| CAMEL-BP-015 | 退出登录/页面切换资源加载慢导致黑屏 | REG-16, REG-26, U16 | none | add-minimal-case |  |
| CAMEL-BP-016 | 无效入口：控件可点但无响应或文案与功能不符 | REG-15, REG-30, U15 | partial | enhance-existing | TC-ADM-01-N |
| CAMEL-BP-017 | 拖拽排序失效或顺序未持久化 | REG-28 | partial | enhance-existing | TC-ADM-34-P |
| CAMEL-BP-018 | 删除后数据不可恢复/不可重建或残留脏数据 | REG-29, D-03 | none | add-minimal-case |  |
| CAMEL-BP-019 | 弹窗内次级动作打断主任务（跳转/关闭上下文丢失） | REG-33 | partial | enhance-existing | TC-MP-51-P |
| CAMEL-BP-020 | 手势/滑动手势区域失效无法浏览 | REG-08, U9 | partial | enhance-existing | TC-DEV-27-P |
| CAMEL-BP-021 | 后端参数校验缺失，非法入参统一 500/NPE | BUG-002, BUG-003, BUG-005, BUG-006 | partial | enhance-existing | TC-API-527871663-04, TC-API-527871571-03 |
| CAMEL-BP-022 | 对象级越权（IDOR）与横向数据访问 | SEC-01, SEC-02 | strong | skip | TC-SEC-02-P, TC-API-527871525-05 |
| CAMEL-BP-023 | 敏感信息明文暴露（Redis/验证码/密钥） | SEC-04, SEC-06, INFRA-01, INFRA-02 | partial | enhance-existing | TC-SEC-03-P, TC-SEC-07-P |
| CAMEL-BP-024 | 业务状态机非法迁移未被拦截 | D-01, D-02 | partial | enhance-existing | TC-D-013, TC-D-018 |
| CAMEL-BP-025 | 统计/计数与实际明细不一致（数据漂移） | D-20 | partial | enhance-existing | TC-MP-73-P, TC-EXT-01-P |
| CAMEL-BP-026 | 大分页/慢接口缺少上限导致长耗时 | D-24, PERF-01 | strong | skip | TC-SEC-03-N |
| CAMEL-BP-027 | 第三方回调验签/异常处理不一致 | CALLBACK-01 | strong | skip | TC-SEC-05-N, TC-API-527871769-02 |
| CAMEL-BP-028 | 后台已发布但 C 端未生效（缓存/版本不一致） | U15, U16, U17, U19 | strong | skip | TC-ADM-34-P, TC-ADM-36-P |
| CAMEL-BP-029 | 前端仅隐藏 UI 未做服务端授权（直连 API 可绕过） | SEC-07, SEC-R2-01 | strong | skip | TC-ADM-06-N, TC-API-527871348-05 |

## 使用规则

1. 只按模块/页面/控件/操作/状态/角色/平台/数据/依赖匹配，不按标题关键词直接判强覆盖。
2. `strong` 只登记关联，不新增用例；`partial` 增强原用例步骤与断言；`none` 且当前需求确实适用才新增最小用例。
3. 通用测试经验标 `GENERIC-RISK`，不得称为项目历史 Bug。
4. 新增/复测缺陷后，用 `bug-pattern-curator` 更新模式与覆盖映射，不在正常生成时挖掘。