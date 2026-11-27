-- 生产 AIQE 只读 role 硬化（由运维在发布窗口执行）
-- 作用：连接级只读 + 5s 语句超时 + 30s 空闲事务超时
-- 注意：SET 只对新连接生效；执行后需重建连接验证。

ALTER ROLE aiqe_ro SET default_transaction_read_only = on;
ALTER ROLE aiqe_ro SET statement_timeout = '5s';
ALTER ROLE aiqe_ro SET idle_in_transaction_session_timeout = '30s';

-- 验证（新连接）：
-- SHOW default_transaction_read_only;  -- 期望 on
-- SHOW statement_timeout;               -- 期望 5s
-- 尝试写入应失败：CREATE TEMP TABLE aiqe_ro_probe(x int);
