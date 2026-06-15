# Architecture Overview

> This document describes the legacy dashboard internals retained during the
> InkPi migration. The current service and module architecture is documented in
> [inkpi-architecture.md](inkpi-architecture.md).

## Goals

- 为 800x480 横屏墨水屏提供可读、低闪烁、可维护的桌面 Dashboard。
- 支持 4 阶灰度渲染、局部刷新和周期性全局刷新。
- 为未来“作为内部服务被其他产品接入”保留清晰的包级接口。

## Instruction Priority

- AI 编码行为规范以 [../.github/copilot-instructions.md](../.github/copilot-instructions.md) 为唯一权威来源。
- 本文档聚焦架构说明；若与权威规范冲突，应先更新权威规范再同步本文。

## Layered Architecture

依赖方向保持单向：`config/domain -> adapters -> services -> application(runtime) -> ui/display`。

### 1. Configuration Layer

- 位置：`src/config.py`
- 职责：集中管理屏幕参数、刷新策略、GitHub/天气/知识卡片等配置。
- 要求：默认可运行，支持环境变量覆盖。

### 2. Domain Layer

- 位置：`src/domain/`
- 职责：定义统一的数据模型（快照、面板数据、刷新决策）。
- 要求：不依赖具体外部 API 与硬件实现。

### 3. Service Layer

- 位置：`src/services/`
- 职责：编排 provider 逻辑、聚合和降级策略（GitHub、天气、时间、系统资源、知识卡片）。
- 要求：每个 provider 可独立替换；失败时返回可降级结果。

### 4. Integration Adapter Layer

- 位置：`src/adapters/`
- 职责：封装外部集成细节（HTTP 端点、分页、超时、请求头）。
- 模块：
  - `open_meteo.py`：天气与地理编码 API。
  - `github_api.py`：GitHub REST API 请求与分页。
  - `knowledge_cards.py`：远程知识卡片 JSON 拉取。
- 要求：不承载业务规则；返回原始/半结构化数据供服务层转换。

### Adapter Injection Rule

- Service 仅依赖 adapter Protocol（接口），不依赖具体 HTTP 类。
- 具体 adapter 实例在 `src/bootstrap.py` 统一装配并注入 service。
- 目标：降低 service 测试成本，便于替换第三方 API 实现。

### 5. Runtime Policy Layer

- 位置：`src/runtime/`
- 职责：封装运行时决策策略，不与硬件和数据实现耦合。
- 模块：
  - `refresh_policy.py`：局刷/全刷时间与计数策略。
  - `ghosting.py`：残影风险判定与局刷历史追踪。
- 要求：仅处理决策状态，不负责 I/O 和依赖构造。

### 6. UI Rendering Layer

- 位置：`src/ui/`
- 职责：按固定布局把领域数据渲染为灰度图像缓冲。
- 布局：
  - 上半区：左侧竖栏（日期/天气/资源）+ 右侧知识卡片
  - 下半区：GitHub 日历 + 组织 repo 数 + 贡献统计

### 7. Display Adapter Layer

- 位置：`src/display/`
- 职责：封装 `waveshare_epd.epd4in26`，统一全刷/局刷接口。
- 要求：隔离硬件细节，便于仿真与测试。

### 8. Application Layer

- 位置：`main.py`, `src/app.py`, `src/bootstrap.py`
- 职责：
  - `main.py`：程序入口（实机模式/预览模式）。
  - `src/bootstrap.py`：依赖装配（composition root）。
  - `src/app.py`：循环编排、生命周期屏幕、信号处理。
- 要求：应用层可编排多个层，但不承载具体业务算法和硬件细节。

## Refresh Strategy

- 局部刷新周期：默认 60 秒（可配置）。
- 强制全刷触发：
  1. 距离上次全刷超过 1 小时。
  2. 局刷次数达到阈值 N（可配置）。
- 决策优先级：全刷触发条件先判定，再判定局刷。

## Runtime Safety Guarantees

- 全刷完成后必须重置局刷计数基线。
- 刷新失败必须记录日志并在下一周期继续重试，不得导致主循环卡死。
- 终止信号（SIGINT/SIGTERM）触发时，应先渲染关机页，再执行显示休眠。

## Extensibility

- 对外暴露内部 Python 包接口（不在首版开放 HTTP）。
- 服务层通过协议接口隔离实现，支持替换数据源。
- 应用层通过 `src/bootstrap.py` 集中依赖构造，降低重复装配与跨层耦合。
