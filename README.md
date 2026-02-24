# eInk Dashboard

桌面墨水屏 Dashboard，目标硬件为树莓派 4B + 微雪 4.26inch（800x480）墨水屏。

## Current Status

- ✅ 已完成：配置系统、刷新策略、所有数据服务（GitHub/天气/系统/知识卡片）、UI渲染管道
- 🚧 进行中：EPD硬件显示适配层、脏区域追踪优化
- 📊 数据源：所有服务均已使用真实数据（GitHub API、Open-Meteo天气、系统负载、本地知识卡片）

## Key Features

- **智能地理编码**：天气位置支持中英文地名（如"上海"、"Shanghai"）或精确坐标
- **时区支持**：可配置显示本地时间（如Asia/Shanghai）
- **灰度渲染**：4级灰度优化布局，适配4.26寸墨水屏可读性
- **双触发刷新策略**：时间触发 OR 次数触发，灵活的全屏/局部刷新机制

## Quick Start

### 1. 安装依赖

```bash
uv python install 3.12
uv python pin 3.12
uv venv
uv sync
```

### 2. 配置环境变量

```bash
cp .env.example .env
# 编辑 .env，设置你的GitHub用户名、组织名和天气位置
```

### 3. 生成预览

```bash
export $(cat .env | xargs)
uv run python preview.py
```

查看生成的 `preview.png` 确认布局效果。

### 4. 运行Dashboard

```bash
uv run python main.py
```

详细配置说明请查看 [使用指南](docs/usage-guide.md)。

## Documentation

- 快速上手：[docs/usage-guide.md](docs/usage-guide.md)
- 架构设计：[docs/architecture-overview.md](docs/architecture-overview.md)
- 开发计划：[docs/development-plan.md](docs/development-plan.md)
- AI协作规范：[docs/ai/instructions/README.md](docs/ai/instructions/README.md)

## Environment Rule

- Python 虚拟环境必须使用 `uv venv` 创建和管理。
- 不使用 `python -m venv`、`virtualenv` 或其他工具创建本项目环境。
