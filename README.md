# eInk Dashboard

桌面墨水屏 Dashboard，目标硬件为树莓派 4B + 微雪 4.26inch（800x480）墨水屏。

## Current Status

- 已完成：项目开发规范文档体系、配置模型、刷新策略骨架、应用启动骨架。
- 进行中：GitHub/天气/知识卡片数据服务、UI 渲染、硬件显示适配层。

## Key Design Constraints

- 屏幕横向放置，分辨率 800x480，4 阶灰度。
- 高频数据使用局部刷新（默认 60s，可配置）。
- 每小时强制全局刷新，并支持每 N 次局刷后强制全刷。
- 代码结构保持可扩展，支持未来作为内部 Python 包被其他产品接入。

## Documentation

- 架构与开发计划见 [docs/README.md](docs/README.md)。
- AI 协作开发规范见 [docs/ai/instructions/README.md](docs/ai/instructions/README.md)。

## Quick Start (uv)

```bash
uv python install 3.12
uv python pin 3.12
uv venv
uv sync
uv run python main.py
```

## Environment Rule

- Python 虚拟环境必须使用 `uv venv` 创建和管理。
- 不使用 `python -m venv`、`virtualenv` 或其他工具创建本项目环境。
