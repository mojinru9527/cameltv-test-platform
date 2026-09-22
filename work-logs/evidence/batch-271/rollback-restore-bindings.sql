-- Batch 271 回滚材料：恢复"已下线菜单 × 角色"的 18 条绑定
-- 来源：解绑前从生产 cameltv_production 导出（2026-09-23）
-- 用法：psql -U cameltv -d cameltv_production -f rollback-restore-bindings.sql
-- 说明：role_id 2 = tester，3 = viewer；ON CONFLICT 保证重复执行安全。
--       本回滚只动 sys_role_permission，不动 sys_permission（权限行从未删除）。

INSERT INTO sys_role_permission (role_id, permission_id) VALUES
    (2, 26),   -- tester × menu:agent-workbench
    (2, 10),   -- tester × menu:knowledge:artifacts
    (2,  9),   -- tester × menu:knowledge:graph
    (2,  8),   -- tester × menu:knowledge:platform
    (2,  7),   -- tester × menu:knowledge:project
    (2, 11),   -- tester × menu:mindmap
    (2, 139),  -- tester × menu:organization
    (2, 27),   -- tester × menu:perftest
    (2, 134),  -- tester × menu:playground
    (2, 16),   -- tester × menu:special
    (2, 13),   -- tester × menu:testplan
    (2,  3),   -- tester × menu:trace
    (3, 10),   -- viewer × menu:knowledge:artifacts
    (3,  9),   -- viewer × menu:knowledge:graph
    (3,  8),   -- viewer × menu:knowledge:platform
    (3,  7),   -- viewer × menu:knowledge:project
    (3, 139),  -- viewer × menu:organization
    (3,  3)    -- viewer × menu:trace
ON CONFLICT (role_id, permission_id) DO NOTHING;
