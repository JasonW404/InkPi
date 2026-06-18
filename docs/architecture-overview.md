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

### 5. Display Engine Layer

- 位置：`inkpi/display/`
- 职责：封装刷新决策策略，不与硬件和数据实现耦合。
- 模块：
  - `engine.py`：脏矩形检测、区域局部刷新、区域修复、自适应刷新。
- 要求：仅处理决策状态，不负责 I/O 和依赖构造。

### 6. UI Rendering Layer

- 位置：`src/ui/`
- 职责：按固定布局把领域数据渲染为灰度图像缓冲。
- 布局：
  - 顶部：日期、时间、天气、版本
  - 主区：GitHub 用户数值看板 + 当月贡献日历
  - 中下区：Codex 用量窗口
  - 底部：系统资源和网络状态

### 7. Display Adapter Layer

- 位置：`src/display/`
- 职责：封装 `waveshare_epd.epd4in26`，统一全刷/局刷接口。
- 要求：隔离硬件细节，便于仿真与测试。

### 8. Application Layer

- 位置：`inkpi/cli.py`, `inkpi/core.py`, `src/bootstrap.py`
- 职责：
  - `inkpi/cli.py`：程序入口（inkpi-core, inkpi-display, inkpi-ctl, inkpi-preview）。
  - `inkpi/core.py`：循环编排、调度、控制 API。
  - `src/bootstrap.py`：依赖装配（composition root）。
- 要求：应用层可编排多个层，但不承载具体业务算法和硬件细节。

## Refresh Strategy

- 脏矩形检测：计算变化像素的边界框，仅刷新变化区域。
- 区域局部刷新：使用 SetWindow 限制物理刷新范围，减少 EPD 刷新面积。
- 区域修复：每 N 次局部刷新后，使用白色基线进行"迷你全局刷新"，清除残影。
- 基线同步：每次局部刷新后将新内容写入 0x26 RAM，防止陈旧差分累积。
- 自适应刷新：按区域跟踪局部刷新次数，智能触发修复。
- 默认配置：
  - 最大局部刷新次数：50（可配置）
  - 区域修复阈值：30 次（可配置）
  - 区域填充：8 像素（可配置）

## Runtime Safety Guarantees

- 全刷完成后必须重置局刷计数基线。
- 刷新失败必须记录日志并在下一周期继续重试，不得导致主循环卡死。
- 终止信号（SIGINT/SIGTERM）触发时，应先渲染关机页，再执行显示休眠。

## Extensibility

- 对外暴露内部 Python 包接口（不在首版开放 HTTP）。
- 服务层通过协议接口隔离实现，支持替换数据源。
- 应用层通过 `src/bootstrap.py` 集中依赖构造，降低重复装配与跨层耦合。
