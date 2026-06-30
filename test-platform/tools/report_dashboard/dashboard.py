"""streamlit 看板：通过率趋势 / flaky 检测 / 按模块归因。由 `tp report serve` 启动。"""
from __future__ import annotations

import sqlite3
from pathlib import Path

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parent.parent.parent
DB = ROOT / "data" / "platform.sqlite"

st.set_page_config(page_title="测试报告看板", layout="wide")
st.title("📊 测试报告聚合看板")

if not DB.exists():
    st.warning("暂无数据。先用 `tp report ingest --file <报告.xml>` 入库。")
    st.stop()

conn = sqlite3.connect(DB)
runs = pd.read_sql_query("SELECT * FROM runs ORDER BY id", conn)
cases = pd.read_sql_query("SELECT * FROM cases", conn)
conn.close()

if runs.empty:
    st.warning("runs 表为空。")
    st.stop()

runs["pass_rate"] = (runs["passed"] / runs["total"] * 100).round(1)

# --- 概览 ---
latest = runs.iloc[-1]
c1, c2, c3, c4 = st.columns(4)
c1.metric("最近通过率", f"{latest['pass_rate']}%")
c2.metric("用例总数", int(latest["total"]))
c3.metric("失败", int(latest["failed"]))
c4.metric("耗时(s)", round(float(latest["duration"]), 1))

# --- 趋势 ---
st.subheader("通过率趋势")
st.line_chart(runs.set_index("build")[["pass_rate"]])
st.subheader("用例数 / 耗时趋势")
st.line_chart(runs.set_index("build")[["total", "duration"]])

# --- flaky 检测（同一用例历史上既有 pass 又有 fail）---
st.subheader("🔁 Flaky 用例")
status_per_case = cases.groupby("name")["status"].agg(lambda s: set(s))
flaky = [n for n, sts in status_per_case.items() if "passed" in sts and "failed" in sts]
if flaky:
    st.dataframe(pd.DataFrame({"flaky 用例": flaky}), use_container_width=True)
else:
    st.success("未检测到 flaky 用例。")

# --- 按模块归因（classname 维度失败统计）---
st.subheader("📦 失败按模块归因")
fails = cases[cases["status"] == "failed"]
if not fails.empty:
    by_mod = fails.groupby("classname").size().sort_values(ascending=False)
    st.bar_chart(by_mod)
else:
    st.success("最近无失败用例。")

# --- 本次 vs 上次新增失败 ---
if len(runs) >= 2:
    st.subheader("本次 vs 上次")
    last_id, prev_id = int(runs.iloc[-1]["id"]), int(runs.iloc[-2]["id"])
    last_fail = set(cases[(cases.run_id == last_id) & (cases.status == "failed")]["name"])
    prev_fail = set(cases[(cases.run_id == prev_id) & (cases.status == "failed")]["name"])
    col_a, col_b = st.columns(2)
    col_a.write("🆕 新增失败"); col_a.write(sorted(last_fail - prev_fail) or "无")
    col_b.write("✅ 修复"); col_b.write(sorted(prev_fail - last_fail) or "无")
