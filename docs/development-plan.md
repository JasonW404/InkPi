# Development Plan

> InkPi 模块化改造的当前架构与交付状态见
> [inkpi-architecture.md](inkpi-architecture.md)。下文保留原 overview
> dashboard 的历史开发计划。

## Phase 0: Foundation (completed)

- [x] 文档框架与架构说明
- [x] 开发规范整合（`.github/copilot-instructions.md`）
- [x] Python 3.12 + uv 基线
- [x] 配置模型与刷新策略骨架

## Phase 1: Data Services

- [x] 统一领域模型（DashboardSnapshot 与面板数据模型）
- [x] 服务契约层（provider protocols）
- [x] 可降级运行的服务占位实现（GitHub/天气/时间/系统/知识卡片）
- [ ] 生产级 API 细节完善（限流、缓存、重试、批量请求优化）

- GitHub：
  - 用户当月提交日历
  - 组织 repo 数
  - 组织所有 repo 当月 commit 总数与代码量总和
- 天气与日期：基于配置地点和时区输出结构化数据
- 系统资源：输出负载等级（每 20% 一档）
- 知识卡片：本地优先、网络覆盖

验收标准：

- 服务层具备统一数据模型与错误降级返回。
- 任一 provider 不可用时，应用仍能渲染并刷新。

## Phase 2: UI + Display

- [x] 固定布局实现（800x480 横屏，4 灰度）
- [x] 面板渲染器（侧边栏/知识卡片/GitHub 统计）
- [x] 主渲染器与应用循环集成
- [x] 布局预览脚本（`preview.py`）
- [x] EPD 适配层（全刷/局刷/4灰度模式）
- [x] 脏区计算与优化
- [ ] 实机集成测试

验收标准：

- 实机可持续运行 24h。
- 局刷节奏稳定，全刷触发正确。
- 布局验证：运行 `uv run python preview.py` 生成 `preview.png`

## Phase 3: Runtime Robustness

- 加入重试与超时策略。
- 增加运行日志与关键指标。
- 增加渲染快照测试与策略单测。

验收标准：

- 关键模块覆盖基础单元测试。
- 运行异常可自动恢复。

## Operational Commands

- Whenever `python` or `pip` commands are required, or any other Python related commands are required, you must use `uv` instead. Refer to [copilot-instructions.md](../.github/copilot-instructions.md)
- Setup baseline:
  - `uv python install 3.12`
  - `uv python pin 3.12`
  - `uv venv`
  - `uv sync`
