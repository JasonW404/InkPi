# Quality Gates

## Before Merge

- 使用 `uv venv` 创建虚拟环境并完成 `uv sync`
- 通过 `uv run ruff check .`
- 通过 `uv run python -m compileall .`
- 新增逻辑至少包含基础测试或可验证运行路径
- 文档与代码保持一致

## Runtime Checks

- 启动时打印关键配置（隐藏敏感信息）
- 刷新日志必须包含：模式、原因、耗时、异常摘要
- provider 错误不应导致进程退出

## Definition of Done

- 功能完成并符合对应规范文档
- 至少一次本地运行验证
- 涉及架构边界改动时，已更新 `docs/` 文档