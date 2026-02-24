# Architecture Overview

## Goals

- 为 800x480 横屏墨水屏提供可读、低闪烁、可维护的桌面 Dashboard。
- 支持 4 阶灰度渲染、局部刷新和周期性全局刷新。
- 为未来“作为内部服务被其他产品接入”保留清晰的包级接口。

## Layered Architecture

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
- 职责：采集并规整数据（GitHub、天气、时间、系统资源、知识卡片）。
- 要求：每个 provider 可独立替换；失败时返回可降级结果。

### 4. UI Rendering Layer

- 位置：`src/ui/`
- 职责：按固定布局把领域数据渲染为灰度图像缓冲。
- 布局：
  - 上半区：左侧竖栏（日期/天气/资源）+ 右侧知识卡片
  - 下半区：GitHub 日历 + 组织 repo 数 + 贡献统计

### 5. Display Adapter Layer

- 位置：`src/display/`（规划中）
- 职责：封装 `waveshare_epd.epd4in26`，统一全刷/局刷接口。
- 要求：隔离硬件细节，便于仿真与测试。

### 6. Application Layer

- 位置：`src/app.py`, `main.py`
- 职责：应用启动、调度循环、刷新策略执行、异常恢复。

## Refresh Strategy

- 局部刷新周期：默认 60 秒（可配置）。
- 强制全刷触发：
  1. 距离上次全刷超过 1 小时。
  2. 局刷次数达到阈值 N（可配置）。
- 决策优先级：全刷触发条件先判定，再判定局刷。

## Extensibility

- 对外暴露内部 Python 包接口（不在首版开放 HTTP）。
- 服务层通过协议接口隔离实现，支持替换数据源。
- 应用层依赖抽象，不直接依赖具体 provider。