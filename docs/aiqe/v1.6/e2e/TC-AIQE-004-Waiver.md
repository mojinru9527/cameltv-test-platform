# TC-AIQE-004 说明（广告范围外 → 其他功能浮层适配）

- 日期：2026-11-27
- 确认人：用户（项目负责人）
- 广告/浮层投放模块**不属于未来娃屿项目**，V5 需求与权威手工验收表均无广告模块。
- 按 TC 标题中的“**其他功能浮层**”做适配验证：使用未来娃屿后台真实命令面板（Ctrl+K）作为浮层。

## 适配结果（PASS）
1. 命令面板浮层可正常打开；
2. 浮层打开时点击底层侧边栏，**未触发底层导航**；
3. Esc 关闭浮层后，底层导航恢复，可进入“轮播图”页面。

- AIQE Run：`aba69181`
- 证据：`docs/aiqe/v1.6/evidence/product/TC-AIQE-004/overlay-interference.json`
- 截图：`docs/aiqe/v1.6/evidence/product/TC-AIQE-004/overlay-interference.png`
- 结论：广告场景不适用；以真实“其他功能浮层”完成交叉干扰验证。
